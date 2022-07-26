from dotenv import load_dotenv
import os
import re
import json
import uuid
import requests
import copy
from azure.ai.textanalytics import ExtractSummaryAction, TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from fastapi_sqlalchemy import DBSessionMiddleware, db
from models import Glossary, Transcript
import requests
from time import time, sleep
s = requests.Session()

load_dotenv()

summarization_key = os.environ.get("AZURE_SUMMARIZATION_KEY")
summarization_endpoint = os.environ.get("SUMMARIZATION_URL")
biterm_url = os.environ.get("BITERM_URL")
biterm_access_token = os.environ.get("BITERM_ACCESS_TOKEN")
suggestion_access_token = os.environ.get("SUGGESTION_ACCESS_TOKEN")
suggestion_start_session_url = os.environ.get("SUGGESTION_API_START_SESSION")
suggestion_closed_session_url = os.environ.get("SUGGESTION_API_CLOSE_SESSION")
suggestion_url = os.environ.get("SUGGESTION_COMPUTE_RESULT_URL")
translation_key = os.environ.get('TRANSLATION_KEY')
translation_region = os.environ.get('TRANSLATION_REGION')
translation_url = os.environ.get('TRANSLATION_URL')
database_url = os.environ.get('DATABASE_URI')


def fill_target_terms(term_values, tgt_lang, src_lang):
    source_terms = []
    for index, term in enumerate(term_values):
        if term['tgt_term'] == '':
            source_terms.append({"text": term['src_term']})

    path = '/translate'
    constructed_url = translation_url + path

    params = {
        'api-version': '3.0',
        'from': src_lang,
        'to': [{tgt_lang}]
    }

    headers = {
        'Ocp-Apim-Subscription-Key': translation_key,
        'Ocp-Apim-Subscription-Region': translation_region,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    import pdb
    pdb.set_trace()
    request = requests.post(constructed_url, params=params,
                            headers=headers, json=source_terms)
    data = request.json()
    target_index = 0
    for index, term in enumerate(term_values):
        if term['tgt_term'] == '':
            term_values[index]['tgt_term'] = data[target_index]['translations'][0]['text']
            target_index += 1
    return term_values


def convert_tm2tb_data_to_dict(src_terms, tgt_terms, src_labels, src_frequencies, src_clusters, origins, frequencies, similarities, ranks):
    return [{'src_term': src_term, 'tgt_term': tgt_term, 'rank': rank, 'src_label': src_label, 'src_frequency': src_frequency, 'src_cluster': src_cluster, 'origin': origin, 'frequency': frequency, 'similarity': similarity}
            for (src_term, tgt_term, rank, src_label, src_frequency, src_cluster, origin, frequency, similarity) in zip(src_terms, tgt_terms, ranks, src_labels, src_frequencies, src_clusters, origins, frequencies, similarities)]


def convert_to_dict(src_terms, tgt_terms):
    return [{'src_term': src_term, 'tgt_term': tgt_term}
            for (src_term, tgt_term) in zip(src_terms, tgt_terms)]


def generate_rank_color_list(ranks):
    color_array = []
    for rank in ranks:
        if rank < 0.1:
            color_array.append("#E8F5E9")
        elif rank < 0.2:
            color_array.append("#C8E6C9")
        elif rank < 0.3:
            color_array.append("#A5D6A7")
        elif rank < 0.4:
            color_array.append("#81C784")
        elif rank < 0.5:
            color_array.append("#66BB6A")
        elif rank < 0.6:
            color_array.append("#4CAF50")
        elif rank < 0.7:
            color_array.append("#43A047")
        elif rank < 0.8:
            color_array.append("#388E3C")
        elif rank < 0.9:
            color_array.append("#2E7D32")
        elif rank < 1.0:
            color_array.append("#1B5E20")
    return color_array


def create_glossary(term_values, src_lang, tgt_lang):
    glossary = {
        "entries": [
        ]
    }
    for term in term_values:
        glossary['entries'].append([{"lang": src_lang, "text": term['src_term']}, {
                                   "lang": tgt_lang, "text": term['tgt_term']}])
    return glossary


def check_keys_validation(keys):
    for key in ['src_texts', 'src_lang', 'tgt_texts', 'tgt_lang', 'freq_min']:
        if key not in keys:
            return False
    return True


def manage_terms_data(data):
    if data['error']:
        return data['data']
    else:
        src_terms = data['data']['src_terms']
        tgt_terms = data['data']['tgt_terms']
        src_labels = data['data']['src_labels']
        src_frequencies = data['data']['src_frequencies']
        src_clusters = data['data']['src_clusters']
        origins = data['data']['origins']
        frequencies = data['data']['frequencies']
        similarities = data['data']['similarities']
        ranks = data['data']['ranks']
        return convert_tm2tb_data_to_dict(src_terms, tgt_terms, src_labels, src_frequencies, src_clusters, origins, frequencies, similarities, ranks)


def extract_terms(data):
    data['mt_unmatched_terms'] = 1
    data['include_entities'] = 1
    try:
        response = requests.post(
            url=f"{biterm_url}?access_token={biterm_access_token}", json=data)
        response_data = response.json()
        error = False
        if response.status_code == 422:
            response_data = []
            error = True
    except Exception:
        error = True
        response_data = []
    context = {"data": response_data, "error": error}
    return context


def text_summarization(document):
    document_results = []
    try:
        client = authenticate_client()
        poller = client.begin_analyze_actions(
            document,
            actions=[
                ExtractSummaryAction(max_sentence_count=20)
            ],
        )
        document_results = poller.result()
    except:
        return {'message': 'Unable to retrieve data from summarization'}
    for result in document_results:
        extract_summary_result = result[0]
        if extract_summary_result.is_error:
            return(f"...Is an error with code {extract_summary_result.code} and message {extract_summary_result.message}")
        else:
            return extract_summary_result.sentences


def authenticate_client():
    ta_credential = AzureKeyCredential(summarization_key)
    text_analytics_client = TextAnalyticsClient(
        endpoint=summarization_endpoint,
        credential=ta_credential)
    return text_analytics_client


def kudo_summarizer(src_lang, src_text, src_terms):
    nr_results = 15
    result = []
    phrases_summarization = {'en': ["what is", "what are", "refers to", "refer to", "is defined as", "are defined as", "is known as", "are known as", "is used to describe",
                                    "are used to describe", "is a term for", "are terms for", "is understood to", "are understood to", "consists of", "consist of",
                                    "is also called", "are also called", "to summarise"]}
    terms_for_summarization = copy.deepcopy(src_terms)
    terms_for_summarization.extend(phrases_summarization[src_lang])
    sentences = src_text[0].split(".")
    for sentence in sentences:
        words = sentence.split(" ")
        numbers = [int(i) for i in words if i.isdigit()]
        sentence = sentence.strip('\n')
        if len(words) > 4 and len(numbers) < 3 and re.search("^[A-Z].*", sentence):
            for phrase in terms_for_summarization:
                if phrase in words:
                    result.append(sentence)
                    nr_results -= 1
                    break
        if nr_results == 0:
            break
    return result


def remove_entities_from_terms(data, indexes):
    correct_index = 0
    for j in indexes:
        j = j - correct_index
        for item in ['src_terms', 'src_labels', 'tgt_terms', 'similarities', 'frequencies', 'ranks']:
            del data['data'][item][j]
        correct_index += 1
    return data


def get_entities(data):
    entities = []
    indexes = []
    if data['data']:
        for i in range(len(data['data']['src_terms'])):
            if data['data']['src_labels'][i] != '':
                entities.append(
                    {'text': data['data']['src_terms'][i], 'entity_type': data['data']['src_labels'][i]})
                indexes.append(i)
    else:
        # flash('Unable to retrieve data from biterms')
        pass
    return [entities, indexes]


def remove_conversions_from_entities(data):
    entities = []
    for i in range(len(data['entities'])):
        entities.append(data['entities'][i]['text'])

    for i in data['conversions']:
        if i['entity'] in entities:
            index = entities.index(i['entity'])
            del data['entities'][index]
    return data


def get_suggestion_session_id(data):

    session_id = ""
    try:
        response = requests.post(
            url=f"{suggestion_start_session_url}?access_token={biterm_access_token}", json=data)
        session_id = response.json()
    except Exception:
        return {'message': 'Unable to start session'}

    try:
        s.sessionid[0]
        del s.sessionid
        s.sessionid = session_id
    except:
        print("not found")
        s.sessionid = session_id
    return {"message": "Session Started."}


def get_suggestion_terms(data):
    try:
        response = requests.post(url=f"{suggestion_url}/{s.sessionid}?access_token={biterm_access_token}", json={
            "lang": data['lang'],
            "text": data['text']
        })
        response_data = response.json()
    except Exception:
        return {'message': 'Unable to retrieve data from suggestion'}
    return response_data


def close_suggestion_session():
    try:
        response = requests.post(
            url=f"{suggestion_closed_session_url}/{s.sessionid}?access_token={biterm_access_token}")
        del s.sessionid
    except Exception:
        return {'message': 'Unable to close the session'}
    return {'message': 'successfully closed the session'}


def get_transcript():
    transcript_data = db.session.query(Transcript).order_by(
        Transcript.id.desc()).first()
    data = {
        "src_texts": [transcript_data.src_text],
        "tgt_texts": [transcript_data.tgt_text],
        "src_lang": transcript_data.src_lang,
        "tgt_lang":  transcript_data.tgt_lang,
        "freq_min":  1,
        "span_range":  (1, 7),
        "similarity_min":  0.9,
        "filter_stopwords":  True,
        "include_entities":  False,
        "collapse_lemmas":  True,
        "return_unmatched_terms":  True,
        "mt_unmatched_terms":  True
    }
    return data, transcript_data.id


def insert_glossary(data, output_data, id):
    terms = convert_to_dict(
        output_data['message']['src_terms'], output_data['message']['tgt_terms'])
    for term in terms:
        db_glossary = Glossary(
            src_lang=data["src_lang"], tgt_lang=data["tgt_lang"], src_term=term['src_term'], tgt_term=term['tgt_term'], transcript_id=id)
        db.session.add(db_glossary)
        db.session.commit()
