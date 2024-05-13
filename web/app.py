import re
import os, sys
from flask import Flask, render_template, jsonify, request
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.logger = None
app.config['DEBUG'] = False

# 模拟日志队列
log_queue = []
working = False


def write_log(_str=None):
    if _str is None:
        with open('logs.log', mode='w', encoding='utf-8') as f:
            ...
    else:
        with open('logs.log', mode='a', encoding='utf-8') as f:
            f.write(_str)


def check_working():
    global working
    try:
        if main_thread.is_alive():
            working = True
        else:
            write_log()
            working = False
    except NameError:
        write_log()
        working = False


@app.route('/run', methods=['GET'])
def run():
    return render_template('result.html', is_disabled=working)


@app.route('/', methods=['GET', 'POST'])
def index():
    check_working()
    global main_thread
    if request.method == 'POST':
        task_id = (request.form.get('task_id'))
        sender = request.form.get('sender')
        passwd = request.form.get('passwd')

        svn_archive = request.form.get('archive_svn') == 'yes'
        send_email_to_all = request.form.get('send_email') == 'yes'
        print(svn_archive, send_email_to_all)
        lock = threading.Lock()
        if not working:
            main_thread = threading.Thread(target=run_work,
                                           args=(lock,
                                                 task_id,
                                                 sender,
                                                 passwd,
                                                 send_email_to_all,
                                                 svn_archive,)
                                           )
            main_thread.start()
        return render_template('result.html', is_disabled=working)
    return render_template('index.html', is_disabled=working)


@app.route('/logs')
def logs():
    global log_queue
    log_queue = []
    with open('logs.log', mode='r', encoding='utf-8') as f:
        logs = f.read()
    if logs:
        log_queue.append(logs)
        return jsonify(log_queue)
    return jsonify([''])


def run_work(lock, task_id, sender, passwd, send_email_to_all, svn_archive):
    with lock:
        from main import main
        main(task_id=task_id, sender=sender, passwd=passwd, email_send_all=send_email_to_all,
             push_to_svn=svn_archive)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
