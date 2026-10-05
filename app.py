from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import data_manager
import os
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')


@app.route('/')
def index():
    topics = data_manager.get_topics()
    stats = data_manager.get_stats()["overall"]
    return render_template('index.html', topics=topics,
                           difficulties=data_manager.DIFFICULTIES,
                           stats=stats)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/start', methods=['POST'])
def start_session():
    mode = request.form.get('mode', 'any')
    topic_id = request.form.get('topic_id', 'all')
    cards = data_manager.get_filtered_cards(mode, topic_id)

    if not cards:
        topics = data_manager.get_topics()
        stats = data_manager.get_stats()["overall"]
        return render_template('index.html', topics=topics,
                               difficulties=data_manager.DIFFICULTIES,
                               stats=stats,
                               error="No cards found for this selection!")

    card_ids = [c['id'] for c in cards]
    random.shuffle(card_ids)

    session['quiz_stack'] = card_ids
    session['current_index'] = 0
    session['mode'] = mode
    session['topic_id'] = topic_id
    return redirect(url_for('quiz'))


@app.route('/quiz')
def quiz():
    stack = session.get('quiz_stack', [])
    idx = session.get('current_index', 0)

    if not stack or idx >= len(stack):
        topics = data_manager.get_topics()
        stats = data_manager.get_stats()["overall"]
        return render_template('index.html', topics=topics,
                               difficulties=data_manager.DIFFICULTIES,
                               stats=stats,
                               message="Session Complete!")

    cards_by_id = {c['id']: c for c in data_manager.get_all_cards()}
    topics_by_id = {t['topic_id']: t for t in data_manager.get_topics()}

    # Skip stale ids (e.g. from results logged against deleted cards).
    while idx < len(stack) and stack[idx] not in cards_by_id:
        idx += 1
    session['current_index'] = idx
    if idx >= len(stack):
        return redirect(url_for('quiz'))

    card = cards_by_id[stack[idx]]
    topic = topics_by_id.get(card.get('topic_id'),
                             {"topic_id": card.get('topic_id'),
                              "topic": "Undefined"})

    return render_template('quiz.html', card=card, topic=topic,
                           progress=f"{idx + 1}/{len(stack)}")


@app.route('/answer', methods=['POST'])
def answer():
    try:
        card_id = int(request.form.get('card_id', ''))
    except (ValueError, TypeError):
        return redirect(url_for('quiz'))
    is_correct = request.form.get('answer') == 'yes'
    data_manager.save_result(card_id, is_correct)
    session['current_index'] = session.get('current_index', 0) + 1
    return redirect(url_for('quiz'))


@app.route('/end')
def end_session():
    session.pop('quiz_stack', None)
    session.pop('current_index', None)
    return redirect(url_for('index'))


@app.route('/stats')
def stats():
    data = data_manager.get_stats()
    return render_template('stats.html', overall=data['overall'],
                           by_topic=data['by_topic'],
                           by_difficulty=data['by_difficulty'])


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', '8001'))
    app.run(host="0.0.0.0", port=port, debug=debug)
