"""
Copyright ©2023. The Regents of the University of California (Regents). All Rights Reserved.

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
from diablo.jobs.tasks.base_task import BaseTask
from diablo.lib.interpolator import interpolate_content
from diablo.merged.emailer import send_system_error_email
from diablo.models.email_template import EmailTemplate
from diablo.models.queued_email import QueuedEmail
from diablo.models.room import Room
from diablo.models.scheduled import Scheduled
from diablo.models.sis_section import SisSection
from flask import current_app as app


class InstructorEmailsTask(BaseTask):

    def _run(self):
        self.term_id = app.config['CURRENT_TERM_ID']
        self.eligible_room_ids = [room.id for room in Room.get_eligible_rooms()]
        self._room_change_alert()

    @classmethod
    def description(cls):
        return f"Queues up '{EmailTemplate.get_template_type_options()['room_change_no_longer_eligible']}' emails."

    def _room_change_alert(self):
        template_type = 'room_change_no_longer_eligible'
        all_scheduled = list(
            filter(
                lambda s: template_type not in (s.alerts or []),
                Scheduled.get_all_scheduled(term_id=self.term_id),
            ),
        )
        if all_scheduled:
            email_template = EmailTemplate.get_template_by_type(template_type)
            courses = SisSection.get_courses(
                include_deleted=True,
                include_non_principal_sections=True,
                include_null_meeting_locations=True,
                section_ids=[s.section_id for s in all_scheduled],
                term_id=self.term_id,
            )
            courses_per_section_id = dict((course['sectionId'], course) for course in courses)
            for scheduled in all_scheduled:
                section_id = scheduled.section_id
                course = courses_per_section_id.get(section_id)
                if course:
                    all_meetings = course['meetings']['eligible'] + course['meetings']['ineligible']
                    all_rooms = [m['room'] for m in all_meetings if m['room']]
                    if not all_rooms:
                        _send_system_error_email(
                            scheduled=scheduled,
                            subject=f'Scheduled course no longer has meeting location (section_id={section_id})',
                        )
                    if self._has_moved_to_ineligible_room(course, scheduled) or course['deletedAt']:
                        if email_template:
                            for instructor in course['instructors']:
                                def _get_interpolate_content(template):
                                    return interpolate_content(
                                        course=course,
                                        publish_type_name=course.get('scheduled', {}).get('publishTypeName'),
                                        recipient_name=instructor['name'],
                                        recording_type_name=course.get('scheduled', {}).get('recordingTypeName'),
                                        templated_string=template,
                                    )
                                QueuedEmail.create(
                                    message=_get_interpolate_content(email_template.message),
                                    recipient=instructor,
                                    section_id=section_id,
                                    subject_line=_get_interpolate_content(email_template.subject_line),
                                    template_type=template_type,
                                    term_id=self.term_id,
                                )
                            Scheduled.add_alert(
                                scheduled_id=course['scheduled']['id'],
                                template_type=template_type,
                            )
                        else:
                            send_system_error_email(f"""
                                No '{template_type}' email template available.
                                We are unable to notify {course['label']} instructors of room change.
                            """)
                else:
                    _send_system_error_email(
                        scheduled=scheduled,
                        subject=f'Scheduled course has no SIS data (section_id={section_id})',
                    )

    def _has_moved_to_ineligible_room(self, course, scheduled):
        eligible_meetings = course['meetings']['eligible']
        has_room_change = scheduled.room_id not in [m.get('room', {}).get('id') for m in eligible_meetings]
        return has_room_change and (not eligible_meetings or scheduled.room_id not in self.eligible_room_ids)


def _send_system_error_email(scheduled, subject):
    base_url = app.config['KALTURA_MEDIA_SPACE_URL']
    kaltura_schedule_id = scheduled.kaltura_schedule_id
    kaltura_url = f'{base_url}/recscheduling/index/edit-event/eventid/{kaltura_schedule_id}'
    message = f"""\n
        Course: {scheduled.course_display_name} (section_id={scheduled.section_id})\n\n
        Instructor UIDs: {', '.join(scheduled.instructor_uids if scheduled.instructor_uids else '&mdash;')}\n\n
        Kaltura schedule ID: {kaltura_schedule_id}\n\n
        Edit Kaltura series: {kaltura_url}\n\n
    """
    app.logger.error(subject)
    send_system_error_email(
        message=message,
        subject=subject,
    )
