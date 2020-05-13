"""
Copyright ©2020. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""
from diablo.api.errors import BadRequestError, ResourceNotFoundError
from diablo.api.util import admin_required
from diablo.jobs.admin_emails_job import AdminEmailsJob
from diablo.jobs.canvas_job import CanvasJob
from diablo.jobs.instructor_emails_job import InstructorEmailsJob
from diablo.jobs.kaltura_job import KalturaJob
from diablo.jobs.queued_emails_job import QueuedEmailsJob
from diablo.jobs.sis_data_refresh_job import SisDataRefreshJob
from diablo.lib.http import tolerant_jsonify
from diablo.models.job_history import JobHistory
from flask import current_app as app

available_jobs = [
    AdminEmailsJob,
    CanvasJob,
    InstructorEmailsJob,
    KalturaJob,
    QueuedEmailsJob,
    SisDataRefreshJob,
]


@app.route('/api/job/<job_key>/start')
@admin_required
def start_job(job_key):
    job_class = next((job for job in available_jobs if job.key() == job_key), None)
    if job_class:
        job_class(app.app_context).run_with_app_context()
        return tolerant_jsonify(_job_class_to_json(job_class))
    else:
        raise ResourceNotFoundError(f'Invalid job_key: {job_key}')


@app.route('/api/job/history/<day_count>')
@admin_required
def job_history(day_count):
    def _raise_error():
        raise BadRequestError(f'Invalid day_count: {day_count}')
    try:
        days = int(day_count)
        if days < 1:
            _raise_error()
        return tolerant_jsonify([h.to_api_json() for h in JobHistory.get_job_history_in_past_days(day_count=days)])
    except ValueError:
        _raise_error()


@app.route('/api/job/schedule')
@admin_required
def job_schedule():
    config = app.config['JOB_MANAGER']
    schedule = {
        'autoStart': config['auto_start'],
        'jobs': [],
        'secondsBetweenJobsCheck': config['seconds_between_pending_jobs_check'],
    }
    for entry in config['jobs']:
        job_class = next((job for job in available_jobs if job.key() == entry['key']), None)
        if job_class:
            schedule['jobs'].append({
                'name': job_class.__name__,
                'description': job_class.description(),
                'schedule': entry['schedule'],
            })
    return tolerant_jsonify(schedule)


@app.route('/api/jobs/available')
@admin_required
def available():
    return tolerant_jsonify([_job_class_to_json(job_class=job_class) for job_class in available_jobs])


def _job_class_to_json(job_class):
    return {
        'key': job_class.key(),
        'class': job_class.__name__,
        'description': job_class.description(),
    }
