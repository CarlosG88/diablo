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
from datetime import datetime

from diablo import db
from diablo.lib.berkeley import get_recording_end_date, get_recording_start_date
from diablo.lib.util import format_days, format_time
from diablo.models.approval import Approval
from diablo.models.canvas_course_site import CanvasCourseSite
from diablo.models.course_preference import CoursePreference
from diablo.models.cross_listing import CrossListing
from diablo.models.room import Room
from diablo.models.scheduled import Scheduled
from diablo.models.sent_email import SentEmail
from flask import current_app as app
from sqlalchemy import text


class SisSection(db.Model):
    __tablename__ = 'sis_sections'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    allowed_units = db.Column(db.String)
    course_name = db.Column(db.String)
    course_title = db.Column(db.Text)
    instruction_format = db.Column(db.String)
    instructor_name = db.Column(db.Text)
    instructor_role_code = db.Column(db.String)
    instructor_uid = db.Column(db.String)
    is_primary = db.Column(db.Boolean)
    is_principal_listing = db.Column(db.Boolean, nullable=False, default=True)
    meeting_days = db.Column(db.String)
    meeting_end_date = db.Column(db.DateTime)
    meeting_end_time = db.Column(db.String)
    meeting_location = db.Column(db.String)
    meeting_start_date = db.Column(db.DateTime)
    meeting_start_time = db.Column(db.String)
    section_id = db.Column(db.Integer, nullable=False)
    section_num = db.Column(db.String)
    term_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __init__(
            self,
            allowed_units,
            course_name,
            course_title,
            instruction_format,
            instructor_name,
            instructor_role_code,
            instructor_uid,
            is_primary,
            meeting_days,
            meeting_end_date,
            meeting_end_time,
            meeting_location,
            meeting_start_date,
            meeting_start_time,
            section_id,
            section_num,
            term_id,
    ):
        self.allowed_units = allowed_units
        self.course_name = course_name
        self.course_title = course_title
        self.instruction_format = instruction_format
        self.instructor_name = instructor_name
        self.instructor_role_code = instructor_role_code
        self.instructor_uid = instructor_uid
        self.is_primary = is_primary
        self.meeting_days = meeting_days
        self.meeting_end_date = meeting_end_date
        self.meeting_end_time = meeting_end_time
        self.meeting_location = meeting_location
        self.meeting_start_date = meeting_start_date
        self.meeting_start_time = meeting_start_time
        self.section_id = section_id
        self.section_num = section_num
        self.term_id = term_id

    def __repr__(self):
        return f"""<SisSection
                    id={self.id}
                    allowed_units={self.allowed_units},
                    course_name={self.course_name},
                    course_title={self.course_title},
                    instruction_format={self.instruction_format},
                    instructor_name={self.instructor_name},
                    instructor_role_code={self.instructor_role_code},
                    instructor_uid={self.instructor_uid},
                    is_primary={self.is_primary},
                    meeting_days={self.meeting_days},
                    meeting_end_date={self.meeting_end_date},
                    meeting_end_time={self.meeting_end_time},
                    meeting_location={self.meeting_location},
                    meeting_start_date={self.meeting_start_date},
                    meeting_start_time={self.meeting_start_time},
                    section_id={self.section_id},
                    section_num={self.section_num},
                    term_id={self.term_id},
                    created_at={self.created_at}>
                """

    @classmethod
    def set_non_principal_listings(cls, section_ids, term_id):
        sql = 'UPDATE sis_sections SET is_principal_listing = FALSE WHERE term_id = :term_id AND section_id  = ANY(:section_ids)'
        db.session.execute(
            text(sql),
            {
                'section_ids': section_ids,
                'term_id': term_id,
            },
        )

    @classmethod
    def get_distinct_meeting_locations(cls):
        sql = """
            SELECT DISTINCT meeting_location FROM sis_sections
            WHERE
                meeting_location IS NOT NULL
                AND meeting_location != ''
                AND instructor_role_code IN ('ICNT', 'PI', 'TNIC')
            ORDER BY meeting_location
        """
        return [row['meeting_location'] for row in db.session.execute(text(sql))]

    @classmethod
    def get_distinct_instructor_uids(cls):
        sql = 'SELECT DISTINCT instructor_uid FROM sis_sections WHERE instructor_uid IS NOT NULL'
        return [row['instructor_uid'] for row in db.session.execute(text(sql))]

    @classmethod
    def get_course(cls, term_id, section_id):
        sql = """
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            WHERE
                s.term_id = :term_id
                AND s.is_primary IS TRUE
                AND s.section_id = :section_id
                AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_principal_listing IS TRUE
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'section_id': section_id,
                'term_id': term_id,
            },
        )
        api_json = _to_api_json(term_id=term_id, rows=rows)
        return api_json[0] if api_json else None

    @classmethod
    def get_course_changes(cls, term_id):
        sql = """
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
            JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = :term_id AND d.deleted_at IS NULL
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            WHERE
                s.term_id = :term_id
                AND s.is_primary IS TRUE
                AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_principal_listing IS TRUE
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        courses = []
        obsolete_instructor_uids = set()

        for course in _to_api_json(term_id=term_id, rows=rows):
            scheduled = course['scheduled']
            if scheduled['hasObsoleteRoom'] \
                    or scheduled['hasObsoleteInstructors'] \
                    or scheduled['hasObsoleteMeetingDates'] \
                    or scheduled['hasObsoleteMeetingTimes']:
                courses.append(course)
            if scheduled['hasObsoleteInstructors']:
                obsolete_instructor_uids.update(scheduled['instructorUids'])
                scheduled['instructors'] = []

        if obsolete_instructor_uids:
            obsolete_instructors = {}
            instructor_query = 'SELECT uid, first_name, last_name from instructors where uid = any(:uids)'
            for row in db.session.execute(text(instructor_query), {'uids': list(obsolete_instructor_uids)}):
                obsolete_instructors[row['uid']] = {
                    'name': ' '.join([row['first_name'], row['last_name']]),
                    'uid': row['uid'],
                }
            for course in courses:
                if course['scheduled']['hasObsoleteInstructors']:
                    course['scheduled']['instructors'] = []
                    for uid in course['scheduled']['instructorUids']:
                        course['scheduled']['instructors'].append(obsolete_instructors.get(uid, {'name': '', 'uid': uid}))

        return courses

    @classmethod
    def get_courses(cls, term_id, section_ids=None):
        params = {'term_id': term_id}
        if section_ids is None:
            # If no section IDs are specified, return any section with at least one eligible room.
            course_filter = f's.section_id IN ({_sections_with_at_least_one_eligible_room()})'
        else:
            course_filter = 's.section_id = ANY(:section_ids)'
            params['section_ids'] = section_ids
        sql = f"""
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND {course_filter}
                AND s.term_id = :term_id
                AND s.is_primary IS TRUE
                AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_principal_listing IS TRUE
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(text(sql), params)
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_courses_invited(cls, term_id):
        sql = """
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
            JOIN sent_emails e ON e.section_id = s.section_id AND e.template_type = 'invitation'
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            -- Omit approved courses, scheduled courses and opt-outs.
            LEFT JOIN approvals a ON a.section_id = s.section_id AND a.term_id = s.term_id AND a.deleted_at IS NULL
            LEFT JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = s.term_id AND d.deleted_at IS NULL
            LEFT JOIN course_preferences cp ON cp.section_id = s.section_id AND cp.term_id = s.term_id AND cp.has_opted_out IS TRUE
            WHERE a.section_id IS NULL AND d.section_id IS NULL and cp.section_id IS NULL
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_eligible_courses_not_invited(cls, term_id):
        sql = f"""
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND s.section_id IN ({_sections_with_at_least_one_eligible_room()})
                AND s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            -- Omit sent invitations, approved courses, scheduled courses and opt-outs.
            LEFT JOIN approvals a ON a.section_id = s.section_id AND a.term_id = s.term_id AND a.deleted_at IS NULL
            LEFT JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = s.term_id AND d.deleted_at IS NULL
            LEFT JOIN sent_emails e on e.section_id = s.section_id AND e.term_id = s.term_id AND e.template_type = 'invitation'
            LEFT JOIN course_preferences cp ON cp.section_id = s.section_id AND cp.term_id = s.term_id AND cp.has_opted_out IS TRUE
            WHERE a.section_id IS NULL AND d.section_id IS NULL AND e.section_id IS NULL AND cp.section_id IS NULL
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_courses_opted_out(cls, term_id):
        sql = f"""
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND s.term_id = :term_id
                AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE
                AND s.is_principal_listing IS TRUE
                AND s.section_id IN ({_sections_with_at_least_one_eligible_room()})
            JOIN course_preferences c ON c.section_id = s.section_id AND c.term_id = :term_id AND c.has_opted_out IS TRUE
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            -- Omit scheduled courses.
            LEFT JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = :term_id AND d.deleted_at IS NULL
            WHERE d.section_id IS NULL
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_courses_partially_approved(cls, term_id):
        # Courses, including scheduled, that have at least one current instructor who has approved, and at least one
        # current instructor who has not approved. Admins and previous instructors are ignored.
        sql = """
            SELECT DISTINCT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location,
                r.capability AS room_capability
            FROM sis_sections s
            JOIN approvals a
                ON s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
                AND a.section_id = s.section_id AND a.term_id = :term_id
                AND a.deleted_at IS NULL
            JOIN instructors i ON i.uid = s.instructor_uid
            -- This second course/instructor join is not for data display purposes, but to screen for the existence
            -- of any current instructor who has not approved.
            JOIN sis_sections s2
                ON s.term_id = s2.term_id AND s.section_id = s2.section_id
                AND s2.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
            JOIN instructors i2 ON
                i2.uid = s2.instructor_uid
                AND i2.uid NOT IN (
                    SELECT approved_by_uid
                    FROM approvals
                    WHERE section_id = s.section_id AND term_id = :term_id
                )
            -- And a final join to ensure that at least one current instructor has approved.
            JOIN sis_sections s3 ON
                s3.term_id = s2.term_id AND s3.section_id = s2.section_id
                AND s3.instructor_uid = a.approved_by_uid
            JOIN rooms r ON r.location = s.meeting_location
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_courses_queued_for_scheduling(cls, term_id):
        sql = """
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN approvals a
                ON s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
                AND a.section_id = s.section_id AND a.term_id = :term_id AND a.deleted_at IS NULL
                AND (
                    -- If approved by an admin, the course is considered queued.
                    s.section_id IN (
                        SELECT DISTINCT s.section_id
                        FROM sis_sections s
                        JOIN approvals a ON a.section_id = s.section_id AND a.term_id = :term_id AND s.term_id = :term_id AND a.deleted_at IS NULL
                        JOIN admin_users au ON a.approved_by_uid = au.uid
                    )
                    -- If not approved by an admin, we must screen out any courses with an instructor who has not approved.
                    OR s.section_id NOT IN (
                        SELECT DISTINCT s.section_id
                        FROM sis_sections s
                        LEFT JOIN approvals a
                            ON a.section_id = s.section_id AND a.term_id = :term_id AND a.approved_by_uid = s.instructor_uid AND a.deleted_at IS NULL
                        WHERE s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                            AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
                            AND a.section_id IS NULL
                    )
                )
            JOIN rooms r ON r.location = s.meeting_location
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            -- Omit scheduled courses.
            LEFT JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = :term_id AND d.deleted_at IS NULL
            WHERE d.section_id IS NULL
            ORDER BY s.course_name, s.section_id, s.instructor_uid, r.capability NULLS LAST
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows)

    @classmethod
    def get_courses_per_instructor_uid(cls, term_id, instructor_uid):
        # Find all section_ids, including cross-listings
        sql = """
            SELECT s.section_id, s.is_principal_listing
            FROM sis_sections s
            JOIN instructors i
                ON i.uid = s.instructor_uid
                AND s.term_id = :term_id
                AND s.is_primary IS TRUE
                AND s.instructor_uid = :instructor_uid
                AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
        """
        non_principal_section_ids = []
        section_ids = []
        for row in db.session.execute(text(sql), {'instructor_uid': instructor_uid, 'term_id': term_id}):
            if row['is_principal_listing'] is False:
                non_principal_section_ids.append(row['section_id'])
            else:
                section_ids.append(row['section_id'])

        if non_principal_section_ids:
            # Instructor is associated with cross-listed section_ids
            sql = f"""
                SELECT section_id
                FROM cross_listings
                WHERE
                    term_id = :term_id
                    AND cross_listed_section_ids && ARRAY[{','.join(str(id_) for id_ in non_principal_section_ids)}]
            """
            for row in db.session.execute(text(sql), {'section_ids': instructor_uid, 'term_id': term_id}):
                section_ids.append(row['section_id'])

        return cls.get_courses(term_id=term_id, section_ids=section_ids)

    @classmethod
    def get_courses_per_location(cls, term_id, location):
        sql = """
            SELECT
                s.*,
                i.dept_code AS instructor_dept_code,
                i.email AS instructor_email,
                i.first_name || ' ' || i.last_name AS instructor_name,
                i.uid AS instructor_uid,
                r.id AS room_id,
                r.location AS room_location
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
                AND s.meeting_location = :location
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            ORDER BY s.meeting_days, s.meeting_start_time, s.section_id
        """
        rows = db.session.execute(
            text(sql),
            {
                'location': location,
                'term_id': term_id,
            },
        )
        return _to_api_json(term_id=term_id, rows=rows, include_rooms=False)

    @classmethod
    def get_courses_scheduled(cls, term_id):
        scheduled_section_ids = list(cls._section_ids_scheduled(term_id))
        return cls.get_courses(term_id, scheduled_section_ids)

    @classmethod
    def get_courses_scheduled_standard_dates(cls, term_id):
        scheduled_section_ids = cls._section_ids_scheduled(term_id)
        nonstandard_dates_section_ids = cls._section_ids_with_nonstandard_dates(term_id)
        section_ids = list(scheduled_section_ids - nonstandard_dates_section_ids)
        return cls.get_courses(term_id, section_ids)

    @classmethod
    def get_courses_scheduled_nonstandard_dates(cls, term_id):
        scheduled_section_ids = cls._section_ids_scheduled(term_id)
        nonstandard_dates_section_ids = cls._section_ids_with_nonstandard_dates(term_id)
        section_ids = list(scheduled_section_ids.intersection(nonstandard_dates_section_ids))
        return cls.get_courses(term_id, section_ids)

    @classmethod
    def get_random_co_taught_course(cls, term_id):
        sql = """
            SELECT section_id FROM (
                SELECT section_id, instructor_uid from sis_sections
                WHERE term_id = :term_id
                AND is_principal_listing IS TRUE
                GROUP BY section_id, instructor_uid
            ) sections_by_instructor
            GROUP BY section_id
            HAVING COUNT(*) > 2
            LIMIT 1
        """
        section_id = db.session.execute(text(sql), {'term_id': term_id}).scalar()
        return cls.get_course(term_id, section_id)

    @classmethod
    def _section_ids_with_nonstandard_dates(cls, term_id):
        if str(term_id) != str(app.config['CURRENT_TERM_ID']):
            app.logger.warn(f'Dates for term id {term_id} not configured; cannot query for nonstandard dates.')
            return set()
        sql = """
            SELECT DISTINCT s.section_id
            FROM sis_sections s
            WHERE s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
                AND (s.meeting_start_date::text NOT LIKE :term_begin OR s.meeting_end_date::text NOT LIKE :term_end)
            ORDER BY s.section_id
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
                'term_begin': f"{app.config['CURRENT_TERM_BEGIN']}%",
                'term_end': f"{app.config['CURRENT_TERM_END']}%",
            },
        )
        return set([row['section_id'] for row in rows])

    @classmethod
    def _section_ids_scheduled(cls, term_id):
        sql = """
            SELECT DISTINCT s.section_id
            FROM sis_sections s
            JOIN rooms r ON r.location = s.meeting_location
                AND s.term_id = :term_id AND s.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
                AND s.is_primary IS TRUE AND s.is_principal_listing IS TRUE
            JOIN scheduled d ON d.section_id = s.section_id AND d.term_id = :term_id AND d.deleted_at IS NULL
            LEFT JOIN instructors i ON i.uid = s.instructor_uid
            ORDER BY s.section_id
        """
        rows = db.session.execute(
            text(sql),
            {
                'term_id': term_id,
            },
        )
        return set([row['section_id'] for row in rows])


def _to_api_json(term_id, rows, include_rooms=True):
    rows = rows.fetchall()
    section_ids = list(set(int(row['section_id']) for row in rows))
    courses_per_id = {}

    # Perform bulk queries and build data structures for feed generation.
    section_ids_opted_out = CoursePreference.get_section_ids_opted_out(term_id=term_id)

    invited_uids_by_section_id = {section_id: [] for section_id in section_ids}
    for invite in SentEmail.get_emails_of_type(section_ids=section_ids, template_type='invitation', term_id=term_id):
        if invite.recipient_uid not in invited_uids_by_section_id[invite.section_id]:
            invited_uids_by_section_id[invite.section_id].append(invite.recipient_uid)

    approval_results = Approval.get_approvals_per_section_ids(section_ids=section_ids, term_id=term_id)
    scheduled_results = Scheduled.get_scheduled_per_section_ids(section_ids=section_ids, term_id=term_id)

    room_ids = set(row['room_id'] for row in rows)
    room_ids.update(a.room_id for a in approval_results)
    room_ids.update(s.room_id for s in scheduled_results)
    rooms = Room.get_rooms(list(room_ids))
    rooms_by_id = {room.id: room for room in rooms}

    approvals_by_section_id = {section_id: [] for section_id in section_ids}
    for approval in approval_results:
        approvals_by_section_id[approval.section_id].append(approval.to_api_json(rooms_by_id=rooms_by_id))

    scheduled_by_section_id = {s.section_id: s.to_api_json(rooms_by_id=rooms_by_id) for s in scheduled_results}

    cross_listings_per_section_id, instructors_per_section_id, canvas_sites_by_section_id = _get_cross_listed_courses(
        section_ids=section_ids,
        term_id=term_id,
        approvals=approvals_by_section_id,
        invited_uids=invited_uids_by_section_id,
    )

    # Construct course objects.
    # If course has multiple instructors or multiple rooms then the section_id will be represented across multiple rows.
    # Multiple rooms are rare, but a course is sometimes associated with both an eligible and an ineligible room. We
    # order rooms in SQL by capability, NULLS LAST, and use scheduling data from the first row available.
    for row in rows:
        section_id = int(row['section_id'])
        if section_id in courses_per_id:
            course = courses_per_id[section_id]
        else:
            # Approvals and scheduled (JSON)
            approvals = approvals_by_section_id.get(section_id)
            scheduled = scheduled_by_section_id.get(section_id)
            # Instructors per cross-listings
            cross_listed_courses = cross_listings_per_section_id.get(section_id, [])
            instructors = instructors_per_section_id.get(section_id, [])
            # Construct course
            course = {
                'allowedUnits': row['allowed_units'],
                'approvals': approvals,
                'canvasCourseSites': canvas_sites_by_section_id.get(section_id, []),
                'courseName': row['course_name'],
                'courseTitle': row['course_title'],
                'crossListings': cross_listed_courses,
                'hasOptedOut': section_id in section_ids_opted_out,
                'instructionFormat': row['instruction_format'],
                'instructors': instructors,
                'invitees': invited_uids_by_section_id.get(section_id),
                'isPrimary': row['is_primary'],
                'label': _construct_course_label(
                    course_name=row['course_name'],
                    instruction_format=row['instruction_format'],
                    section_num=row['section_num'],
                    cross_listings=cross_listed_courses,
                ),
                'meetings': {
                    'eligible': [],
                    'ineligible': [],
                },
                'nonstandardMeetingDates': False,
                'sectionId': section_id,
                'sectionNum': row['section_num'],
                'scheduled': scheduled,
                'termId': row['term_id'],
            }
            courses_per_id[section_id] = course

        # Note: Instructors associated with cross-listings are slurped up separately.
        instructor_uid = row['instructor_uid']
        if instructor_uid and instructor_uid not in [i['uid'] for i in course['instructors']]:
            course['instructors'].append(
                _to_instructor_json(
                    row=row,
                    approvals=course['approvals'],
                    invited_uids=course['invitees'],
                ),
            )

        meeting = _to_meeting_json(row)
        if not next((m for m in (course['meetings']['eligible'] + course['meetings']['ineligible']) if meeting.items() <= m.items()), None):
            room = rooms_by_id.get(row['room_id']) if 'room_id' in row else None
            if room and room.capability:
                meeting['eligible'] = True
                meeting.update({
                    'recordingEndDate': datetime.strftime(get_recording_end_date(meeting), '%Y-%m-%d'),
                    'recordingStartDate': datetime.strftime(get_recording_start_date(meeting), '%Y-%m-%d'),
                })
                course['meetings']['eligible'].append(meeting)
                course['meetings']['eligible'].sort(key=lambda m: f"{m['startDate']} {m['startTime']}")
                if meeting['startDate'] != app.config['CURRENT_TERM_BEGIN'] or meeting['endDate'] != app.config['CURRENT_TERM_END']:
                    course['nonstandardMeetingDates'] = True
            else:
                meeting['eligible'] = False
                course['meetings']['ineligible'].append(meeting)
                course['meetings']['ineligible'].sort(key=lambda m: f"{m['startDate']} {m['startTime']}")
            if include_rooms:
                meeting['room'] = room.to_api_json() if room else None

    # Next, construct the feed
    api_json = []
    for section_id, course in courses_per_id.items():
        _decorate_course(course)
        # Add course to the feed
        api_json.append(course)

    return api_json


def _decorate_course(course):
    _decorate_course_approvals(course)
    _decorate_course_scheduling(course)
    _decorate_course_changes(course)
    _decorate_course_meeting_type(course)


def _decorate_course_approvals(course):
    course['hasNecessaryApprovals'] = False
    if any(a['wasApprovedByAdmin'] for a in course['approvals']):
        course['hasNecessaryApprovals'] = True

    course['approvalStatus'] = 'Not Invited'
    if course['instructors']:
        approval_uids = [a['approvedBy']['uid'] for a in course['approvals']]
        necessary_approval_uids = [i['uid'] for i in course['instructors']]
        if all(uid in approval_uids for uid in necessary_approval_uids):
            course['approvalStatus'] = 'Approved'
            course['hasNecessaryApprovals'] = True
        elif any(uid in approval_uids for uid in necessary_approval_uids):
            course['approvalStatus'] = 'Partially Approved'
        elif course['invitees']:
            course['approvalStatus'] = 'Invited'


def _decorate_course_scheduling(course):
    course['schedulingStatus'] = 'Not Scheduled'
    if course['scheduled']:
        course['schedulingStatus'] = 'Scheduled'
    elif course['hasNecessaryApprovals']:
        course['schedulingStatus'] = 'Queued for Scheduling'


def _decorate_course_changes(course):
    meetings = course['meetings']['eligible'] + course['meetings']['ineligible']
    if meetings:
        meeting = meetings[0]
        course_meeting_date = '-'.join(
            [
                datetime.strftime(get_recording_start_date(meeting), '%Y-%m-%d'),
                datetime.strftime(get_recording_end_date(meeting), '%Y-%m-%d'),
            ],
        )
        course_meeting_time = '-'.join(
            [
                str(meeting['daysFormatted']),
                str(meeting['startTimeFormatted']),
                str(meeting['endTimeFormatted']),
            ],
        )
        room_id = meeting.get('room', {}).get('id')
    else:
        course_meeting_date = '-'
        course_meeting_time = '-'
        room_id = None

    if course['scheduled']:
        scheduled_meeting_date = '-'.join(
            [
                course['scheduled']['meetingStartDate'],
                course['scheduled']['meetingEndDate'],
            ],
        )
        scheduled_meeting_time = '-'.join(
            [
                str(course['scheduled']['meetingDays']),
                course['scheduled']['meetingStartTime'],
                course['scheduled']['meetingEndTime'],
            ],
        )
        instructor_uids = [i['uid'] for i in course['instructors']]
        has_obsolete_instructors = set(instructor_uids) != set(course.get('scheduled').get('instructorUids'))

        course['scheduled'].update({
            'hasObsoleteInstructors': has_obsolete_instructors,
            'hasObsoleteMeetingDates': course_meeting_date != scheduled_meeting_date,
            'hasObsoleteMeetingTimes': course_meeting_time != scheduled_meeting_time,
            'hasObsoleteRoom': room_id != course.get('scheduled').get('room', {}).get('id'),
        })

    for approval in course['approvals']:
        approval['hasObsoleteRoom'] = room_id != approval.get('room', {}).get('id')


def _decorate_course_meeting_type(course):
    # 'meetingType' is our own homegrown typology. See DIABLO-436.
    if len(course['meetings']['eligible']) > 1:
        course['meetingType'] = 'D'
    elif course['nonstandardMeetingDates']:
        course['meetingType'] = 'C'
    elif len(course['meetings']['eligible'] + course['meetings']['ineligible']) > 1:
        course['meetingType'] = 'B'
    else:
        course['meetingType'] = 'A'


def _get_cross_listed_courses(section_ids, term_id, approvals, invited_uids):
    # Return course and instructor info for cross-listings, and Canvas site info for cross-listings as well as the
    # principal section. Although cross-listed sections were "deleted" during SIS data refresh job, we still rely
    # on metadata from those deleted records.
    cross_listings_by_section_id = CrossListing.get_cross_listings_for_section_ids(section_ids=section_ids, term_id=term_id)
    all_cross_listing_ids = list(set(section_id for k, v in cross_listings_by_section_id.items() for section_id in v))
    all_section_ids = list(set(section_ids + all_cross_listing_ids))

    sql = """
        SELECT
            s.*,
            i.dept_code AS instructor_dept_code,
            i.email AS instructor_email,
            i.first_name || ' ' || i.last_name AS instructor_name,
            i.uid AS instructor_uid
        FROM sis_sections s
        LEFT JOIN instructors i ON i.uid = s.instructor_uid
        WHERE
            s.term_id = :term_id
            AND s.is_primary IS TRUE
            AND section_id = ANY(:all_cross_listing_ids)
        ORDER BY course_name, section_id
    """
    rows = db.session.execute(
        text(sql),
        {
            'all_cross_listing_ids': all_cross_listing_ids,
            'term_id': term_id,
        },
    )
    rows_by_cross_listing_id = {section_id: [] for section_id in all_cross_listing_ids}
    for row in rows:
        rows_by_cross_listing_id[row['section_id']].append(row)

    canvas_sites_by_cross_listing_id = {section_id: [] for section_id in all_section_ids}
    for site in CanvasCourseSite.get_canvas_course_sites(section_ids=all_section_ids, term_id=term_id):
        canvas_sites_by_cross_listing_id[site.section_id].append({
            'courseSiteId': site.canvas_course_site_id,
            'courseSiteName': site.canvas_course_site_name,
        })

    courses_by_section_id = {}
    instructors_by_section_id = {}
    canvas_sites_by_section_id = {}

    # First, collect Canvas sites associated with principal section ids.
    for section_id in section_ids:
        canvas_sites_by_section_id[section_id] = []
        for canvas_site in canvas_sites_by_cross_listing_id.get(section_id, []):
            canvas_sites_by_section_id[section_id].append(canvas_site)

    # Next, collect course data, instructor data, and Canvas sites associated with cross-listings.
    for section_id, cross_listing_ids in cross_listings_by_section_id.items():
        approvals_for_section = approvals.get(section_id, [])
        invited_uids_for_section = invited_uids.get(section_id, [])
        courses_by_section_id[section_id] = []
        instructors_by_section_id[section_id] = []
        for cross_listing_id in cross_listing_ids:
            if rows_by_cross_listing_id[cross_listing_id]:
                # Our first row provides course-specific data.
                row = rows_by_cross_listing_id[cross_listing_id][0]
                courses_by_section_id[section_id].append({
                    'courseName': row['course_name'],
                    'courseTitle': row['course_title'],
                    'instructionFormat': row['instruction_format'],
                    'sectionNum': row['section_num'],
                    'isPrimary': row['is_primary'],
                    'label': f"{row['course_name']}, {row['instruction_format']} {row['section_num']}",
                    'sectionId': row['section_id'],
                    'termId': row['term_id'],
                })
                # Instructor-specific data may be spread across multiple rows.
                for row in rows_by_cross_listing_id[cross_listing_id]:
                    if row['instructor_uid'] and row['instructor_uid'] not in [i['uid'] for i in instructors_by_section_id[section_id]]:
                        instructors_by_section_id[section_id].append(
                            _to_instructor_json(row, approvals_for_section, invited_uids=invited_uids_for_section),
                        )
                for canvas_site in canvas_sites_by_cross_listing_id[cross_listing_id]:
                    canvas_sites_by_section_id[section_id].append(canvas_site)

    return courses_by_section_id, instructors_by_section_id, canvas_sites_by_section_id


def _sections_with_at_least_one_eligible_room():
    return """
        SELECT DISTINCT s2.section_id
        FROM sis_sections s2 JOIN rooms r2
            ON r2.location = s2.meeting_location
            AND r2.capability IS NOT NULL
            AND s2.term_id = :term_id
            AND s2.is_primary IS TRUE
            AND s2.instructor_role_code IN ('ICNT', 'PI', 'TNIC')
            AND s2.is_principal_listing IS TRUE"""


def _to_instructor_json(row, approvals, invited_uids):
    instructor_uid = row['instructor_uid']
    return {
        'approval': next((a for a in approvals if a['approvedBy']['uid'] == instructor_uid), False),
        'deptCode': row['instructor_dept_code'],
        'email': row['instructor_email'],
        'name': row['instructor_name'],
        'roleCode': row['instructor_role_code'],
        'uid': instructor_uid,
        'wasSentInvite': instructor_uid in invited_uids,
    }


def _to_meeting_json(row):
    end_date = row['meeting_end_date']
    start_date = row['meeting_start_date']
    return {
        'days': row['meeting_days'],
        'daysFormatted': format_days(row['meeting_days']),
        'endDate': end_date and datetime.strftime(end_date, '%Y-%m-%d'),
        'endTime': row['meeting_end_time'],
        'endTimeFormatted': format_time(row['meeting_end_time']),
        'location': row['meeting_location'],
        'startDate': start_date and datetime.strftime(start_date, '%Y-%m-%d'),
        'startTime': row['meeting_start_time'],
        'startTimeFormatted': format_time(row['meeting_start_time']),
    }


def _merge_distinct(label, other_labels):
    if label in other_labels:
        other_labels.remove(label)
    return [label] + list(set(other_labels))


def _construct_course_label(course_name, instruction_format, section_num, cross_listings):
    def _label(course_name_, instruction_format_, section_num_):
        return f'{course_name_}, {instruction_format_} {section_num_}'

    if cross_listings:
        merged = _merge_distinct(
            _label(course_name, instruction_format, section_num),
            [_label(c['courseName'], c['instructionFormat'], c['sectionNum']) for c in cross_listings],
        )
        return ' | '.join(merged)
    else:
        return _label(course_name, instruction_format, section_num)
