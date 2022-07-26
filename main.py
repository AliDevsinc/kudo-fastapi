from fastapi import FastAPI, Response
from helpers import *
from constants import *
from utils import *
from time import time, sleep
from tasks import run
# from models import Meeting, Transcript, Glossary
from fastapi_sqlalchemy import DBSessionMiddleware, db


app = FastAPI()

app.add_middleware(DBSessionMiddleware,
                   db_url=database_url)


@app.post("/biterm-celery/")
async def biterm():
    while True:
        data, id = get_transcript()
        result = run.delay(data)
        output_data = result.get()
        insert_glossary(data, output_data, id)
        sleep(60 - time() % 60)
    return {'message': 'successfully'}


# @app.post('/glossary/')
# async def glossary():
#     db_glossary = Glossary(
#         src_lang='en', tgt_lang='fr', src_term='apple', tgt_term='mango', transcript_id=1)
#     db.session.add(db_glossary)
#     db.session.commit()
#     return {'message': 'glossary successfully inserted'}


# @app.post('/meeting/')
# async def meeting():
#     db_meeting = Meeting(title='development',
#                          description='this meeting is about development')
#     db.session.add(db_meeting)
#     db.session.commit()
#     return {'message': 'meeting successfully inserted'}


# @app.post('/transcript/',)
# async def transcript():
#     db_transcript = Transcript(src_text="I have no preference if you think of a question in the middle, feel free to just raise your hand or interrupt.\nEither one is fine. OK, sounds great. Here we go.\nSoum\nI'll have to share it with the screen like this. Hope that's OK. So yeah, welcome to my presentation on Agile product development. Here I will discuss the framework of agile and how the technology team, and more specifically my own tech team, uses these practices.\nWe had a few meetings in the last few weeks where we actually were changing some of the ways that we followed agile and it kind of goes to show how this can be so different for each and every team, so I'll kind of explain you know what agile is and how we can you know, tweak it to make sure that it really is beneficial for ourselves and our team.\nSo little bit of the agenda here what is agile? I'll talk about the common terminology that we use. I'll go into the Scrum framework and the idea of sprints.",
#                                tgt_text="Je vais donc partager mon écran, Bonjour donc ma présentation du développement de produits adjaye. Je vais parler de notre cadre de développement agile et comment notre équipe de technologie.\nUtilise en fait ce logiciel. Nous avons quelques réunions ces dernières années.\nDonc vous pouvez voir comment vous allez voir comment les différentes en fait entre les différentes équipes.\nEt comment nous utilisons ce logiciel dans notre équipe, donc\nAujourd'hui, vous allez voir à l'ordre du jour, qu'est ce que elle a le\nJe vais donc vous parler de comment nous utilisons adjaye les terres, les mots, la terminologie que nous utilisons, les cadres de développement et, et cetera, et cetera. Donc commençons par le début, qu'est ce que j'aille à Gmail est un cadre de développement qui permet de découper.\nUn objectif final en plusieurs sprints où cycles et nous.\nNous avons, nous parlerons plus avant de ces cycles.",
#                                src_lang='en', tgt_lang='fr', meeting_id=1)
#     db.session.add(db_transcript)
#     db.session.commit()
#     return {'message': "successfully"}


@app.post("/biterm-api/", response_model=Tm2tbTerms)
async def biterm_api(item: Item):
    item_dict = item.dict()
    data = extract_terms(item_dict)
    data_list = get_entities(data)
    terms_final_data = remove_entities_from_terms(
        data, data_list[1])
    suggestion_data = data_list[0]
    term_data = manage_terms_data(terms_final_data)
    return {'terms': term_data}


@app.post("/summary/", response_model=SummaryResponse)
async def summary(input: SummaryInput):
    summarization_text = text_summarization([input.source_text])
    return {'summary': summarization_text}


@app.post('/start-session', response_model=StartSessionResponse)
async def startSession(response: Response):
    return get_suggestion_session_id(START_SESSION_GLOSSARY)


@app.post('/suggestion-terms')
def startSession(term: SuggestionTerm):
    data = {}
    data['lang'] = term.lang
    data['text'] = term.text
    return get_suggestion_terms(data)


@app.post('/close-session', response_model=CloseSessionResponse)
def closeSession():
    return close_suggestion_session()
