from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)


# 数据库模型
class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), default='GET')
    expected_status = db.Column(db.Integer, nullable=False)
    expected_response = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20))  # success/failure/error
    actual_response = db.Column(db.Text)
    duration = db.Column(db.Float)  # 请求耗时


# 定时任务
def execute_test_case(case):
    try:
        start_time = datetime.now()
        response = requests.request(
            method=case.method,
            url=case.url,
            timeout=10
        )
        duration = (datetime.now() - start_time).total_seconds()

        actual_response = response.text[:500]  # 截取前500字符
        status = 'success' if (
                response.status_code == case.expected_status and
                response.text == case.expected_response
        ) else 'failure'

    except Exception as e:
        status = 'error'
        actual_response = str(e)
        duration = 0

    return TestResult(
        case_id=case.id,
        status=status,
        actual_response=actual_response,
        duration=duration
    )


def run_daily_tests():
    with app.app_context():
        active_cases = TestCase.query.filter_by(is_active=True).all()
        results = [execute_test_case(case) for case in active_cases]

        db.session.bulk_save_objects(results)
        db.session.commit()


scheduler = BackgroundScheduler()
scheduler.add_job(run_daily_tests, 'cron', hour=2)
scheduler.start()


# 网页路由
@app.route('/')
def dashboard():
    total_cases = TestCase.query.count()
    active_cases = TestCase.query.filter_by(is_active=True).count()
    last_result = TestResult.query.order_by(TestResult.timestamp.desc()).first()

    # 统计最近一次测试结果
    if last_result:
        last_run = last_result.timestamp
        last_results = TestResult.query.filter(
            TestResult.timestamp == last_run
        ).all()
        success = sum(1 for r in last_results if r.status == 'success')
        failure = sum(1 for r in last_results if r.status == 'failure')
        error = sum(1 for r in last_results if r.status == 'error')
    else:
        last_run = None
        success = failure = error = 0

    return render_template('index.html',
                           total=total_cases,
                           active=active_cases,
                           last_run=last_run,
                           success=success,
                           failure=failure,
                           error=error)


@app.route('/cases')
def case_management():
    cases = TestCase.query.order_by(TestCase.created_at.desc()).all()
    return render_template('cases.html', cases=cases)


@app.route('/case/add', methods=['POST'])
def add_case():
    new_case = TestCase(
        name=request.form['name'],
        url=request.form['url'],
        method=request.form['method'],
        expected_status=int(request.form['expected_status']),
        expected_response=request.form['expected_response']
    )
    db.session.add(new_case)
    db.session.commit()
    return redirect(url_for('case_management'))


@app.route('/case/edit/<int:case_id>', methods=['GET', 'POST'])
def edit_case(case_id):
    case = TestCase.query.get_or_404(case_id)
    if request.method == 'POST':
        case.name = request.form['name']
        case.url = request.form['url']
        case.method = request.form['method']
        case.expected_status = int(request.form['expected_status'])
        case.expected_response = request.form['expected_response']
        case.is_active = 'is_active' in request.form
        db.session.commit()
        return redirect(url_for('case_management'))
    return render_template('edit_case.html', case=case)


@app.route('/case/delete/<int:case_id>')
def delete_case(case_id):
    case = TestCase.query.get_or_404(case_id)
    db.session.delete(case)
    db.session.commit()
    return redirect(url_for('case_management'))


@app.route('/results')
def test_results():
    results = TestResult.query.order_by(TestResult.timestamp.desc()).all()
    return render_template('results.html', results=results)


if __name__ == '__main__':
    app.run(debug=True)