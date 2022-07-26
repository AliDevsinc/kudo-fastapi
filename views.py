import os
import simplejson as json
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import logout_user
from requests import post
from dbm_app.decorators import roles_required
from dbm_app.helpers import *
from threading import Thread
logging_info()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        form_data = request.form.to_dict()
        email = form_data.get("email", None)
        password = form_data.get("password", None)
        if email and password:
            app.logger.info(f"User email: {email}")
            response = login_authentication(email, password)
            if response['status'] in ['user unkown', 'not allowed']:
                flash('Invalid username or password')
                return redirect(url_for('login'))
            else:
                session.clear()
                # localStorage.clear()
                delete_firebase_data()
                session["role"] = response['role']
                return redirect(url_for(session["role"]))
        else:
            flash('Empty username or password')
            return redirect(url_for('login'))
    return render_template('login.html', title='Login')


@app.route('/admin', methods=['GET', 'POST'])
@roles_required(["admin"])
def admin():
    if request.method == 'POST':
        app.logger.info("Report processing")
        json_file = request.files['jsonFile']
        app.logger.info(f"File Name: {json_file.filename}")
        if json_file.filename not in session:
            # localStorage.clear()
            delete_firebase_data()
            session[json_file.filename] = json_file.filename
            json_file = json.load(json_file)
            if check_keys_validation(json_file.keys()):
                src_text = json_file['src_texts']
                summarization_execution_time = Thread(
                    target=text_summarization, args=(src_text, ))
                summarization_execution_time.start()
                data = extract_terms(json_file)
                summarization_execution_time.join(20)
                summarization_text = summarization_text_queue.pop()
                if summarization_text == 'No':
                    summarization_text = kudo_summarizer(
                        json_file['src_lang'], src_text, data['data']['src_terms'])
                firebase_object.document("summarization_text").set({"summarization_text":summarization_text})
                # localStorage.setItem('summarization_text', summarization_text)
                data_list = get_entities(data)
                terms_final_data = remove_entities_from_terms(
                    data, data_list[1])
                firebase_object.document("suggestion_data").set({"suggestion_data":data_list[0]})
                # localStorage.setItem('suggestion_data', data_list[0])
                term_data = manage_terms_data(terms_final_data)
                term_values = fill_target_terms(
                    term_data, json_file['tgt_lang'], json_file['src_lang'])
                firebase_object.document("term_values").set({"term_values":term_values})
                # localStorage.setItem('term_values', term_values)
                glossary = create_glossary(
                    term_values, json_file['src_lang'], json_file['tgt_lang'])
                handle_session_id(get_suggestion_session_id(glossary))
                flash('Transcription successfully uploaded')
            else:
                flash('file format is invalid please try again')
                return render_template('welcome.html')
        else:
            session.pop(json_file.filename)
            return render_template('welcome.html')
    return render_template('welcome.html')


@app.route('/ai_report', methods=['GET'])
@roles_required("admin")
def ai_report():
    return render_template('ai_report.html', term_values=fetch_data_from_local_storage("term_values"), summarization_text=fetch_data_from_local_storage("summarization_text"), suggestion_data=fetch_data_from_local_storage("suggestion_data"))


@app.route('/live_suggestions', methods=['GET', 'POST'])
@roles_required("admin")
def live_suggestions():
    return render_template('live_suggestions.html')


@app.route('/live_suggestions_api', methods=['POST'])
def live_suggestions_api():
    content = request.json
    suggestion_data = get_suggestion_terms(content)
    if 'detail' not in suggestion_data and 'message' not in suggestion_data:
        return remove_conversions_from_entities(suggestion_data)
    return suggestion_data


@app.route('/close_suggestions_session', methods=['POST'])
def close_suggestions_session():
    return close_suggestion_session()


@app.route('/user_type_a')
@roles_required(["user_type_a", "admin"])
def user_type_a():
    return('user type a view')


@app.route('/user_type_b')
@roles_required(["user_type_b", "admin"])
def user_type_b():
    return('user type b view')


@app.route('/user_type_ab')
@roles_required(["user_type_a", "admin"])
def user_type_ab():
    return('user type a b view')


@app.route('/logout')
def logout():
    session.clear()
    # localStorage.clear()
    delete_firebase_data()
    logout_user()
    return redirect(url_for('login'))


def login_authentication(email, password):
    url = os.environ.get("AUTHENTICATION_API")
    data = {
        "mail": email,
        "pwd": password
    }
    response = post(url, json=data).json()
    return response
