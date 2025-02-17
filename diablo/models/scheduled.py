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
from datetime import datetime

from diablo import db, std_commit
from diablo.lib.util import format_days, format_time, get_names_of_days, to_isoformat
from diablo.models.approval import NAMES_PER_PUBLISH_TYPE, NAMES_PER_RECORDING_TYPE, publish_type, recording_type
from diablo.models.email_template import email_template_type
from diablo.models.room import Room
from sqlalchemy import and_, text
from sqlalchemy.dialects.postgresql import ARRAY


class Scheduled(db.Model):
    __tablename__ = 'scheduled'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    section_id = db.Column(db.Integer, nullable=False)
    term_id = db.Column(db.Integer, nullable=False)
    alerts = db.Column(ARRAY(email_template_type))
    course_display_name = db.Column(db.String, nullable=False)
    instructor_uids = db.Column(ARRAY(db.String(80)), nullable=False)
    kaltura_schedule_id = db.Column(db.Integer, nullable=False)
    meeting_days = db.Column(db.String, nullable=False)
    meeting_end_date = db.Column(db.DateTime, nullable=False)
    meeting_end_time = db.Column(db.String, nullable=False)
    meeting_start_date = db.Column(db.DateTime, nullable=False)
    meeting_start_time = db.Column(db.String, nullable=False)
    publish_type = db.Column(publish_type, nullable=False)
    recording_type = db.Column(recording_type, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __init__(
            self,
            course_display_name,
            instructor_uids,
            kaltura_schedule_id,
            meeting_days,
            meeting_end_date,
            meeting_end_time,
            meeting_start_date,
            meeting_start_time,
            publish_type_,
            recording_type_,
            room_id,
            section_id,
            term_id,
    ):
        self.course_display_name = course_display_name
        self.instructor_uids = instructor_uids
        self.kaltura_schedule_id = kaltura_schedule_id
        self.meeting_days = meeting_days
        self.meeting_end_date = meeting_end_date
        self.meeting_end_time = meeting_end_time
        self.meeting_start_date = meeting_start_date
        self.meeting_start_time = meeting_start_time
        self.publish_type = publish_type_
        self.recording_type = recording_type_
        self.room_id = room_id
        self.section_id = section_id
        self.term_id = term_id

    def __repr__(self):
        return f"""<Scheduled
                    id={self.id},
                    alerts={', '.join(self.alerts or [])},
                    course_display_name={self.course_display_name},
                    created_at={self.created_at},
                    instructor_uids={', '.join(self.instructor_uids)},
                    kaltura_schedule_id={self.kaltura_schedule_id}
                    meeting_days={self.meeting_days},
                    meeting_end_date={self.meeting_end_date},
                    meeting_end_time={self.meeting_end_time},
                    meeting_start_date={self.meeting_start_date},
                    meeting_start_time={self.meeting_start_time},
                    publish_type={self.publish_type},
                    recording_type={self.recording_type},
                    room_id={self.room_id},
                    section_id={self.section_id},
                    term_id={self.term_id}>
                """

    @classmethod
    def create(
            cls,
            course_display_name,
            instructor_uids,
            kaltura_schedule_id,
            meeting_days,
            meeting_end_date,
            meeting_end_time,
            meeting_start_date,
            meeting_start_time,
            publish_type_,
            recording_type_,
            room_id,
            section_id,
            term_id,
    ):
        scheduled = cls(
            course_display_name=course_display_name,
            instructor_uids=instructor_uids,
            kaltura_schedule_id=kaltura_schedule_id,
            meeting_days=meeting_days,
            meeting_end_date=meeting_end_date,
            meeting_end_time=meeting_end_time,
            meeting_start_date=meeting_start_date,
            meeting_start_time=meeting_start_time,
            publish_type_=publish_type_,
            recording_type_=recording_type_,
            room_id=room_id,
            section_id=section_id,
            term_id=term_id,
        )
        db.session.add(scheduled)
        std_commit()
        return scheduled

    @classmethod
    def get_all_scheduled(cls, term_id):
        return cls.query.filter_by(term_id=term_id, deleted_at=None).all()

    @classmethod
    def get_scheduled_per_section_ids(cls, section_ids, term_id):
        criteria = and_(cls.section_id.in_(section_ids), cls.term_id == term_id, cls.deleted_at == None)  # noqa: E711
        return cls.query.filter(criteria).order_by(cls.created_at).all()

    @classmethod
    def get_scheduled(cls, section_id, term_id):
        return cls.query.filter_by(section_id=section_id, term_id=term_id, deleted_at=None).first()

    @classmethod
    def delete(cls, section_id, term_id):
        sql = """UPDATE scheduled SET deleted_at = now()
            WHERE term_id = :term_id AND section_id = :section_id AND deleted_at IS NULL"""
        db.session.execute(
            text(sql),
            {
                'section_id': section_id,
                'term_id': term_id,
            },
        )

    @classmethod
    def add_alert(cls, scheduled_id, template_type):
        row = cls.query.filter_by(id=scheduled_id).first()
        if row.alerts:
            row.alerts = list(set(row.alerts + [template_type]))
        else:
            row.alerts = [template_type]
        db.session.add(row)
        std_commit()

    def to_api_json(self, rooms_by_id=None):
        room_feed = None
        if self.room_id:
            if rooms_by_id:
                room_feed = rooms_by_id.get(self.room_id, None).to_api_json()
            else:
                room_feed = Room.get_room(self.room_id).to_api_json()
        formatted_days = format_days(self.meeting_days)
        return {
            'id': self.id,
            'alerts': self.alerts or [],
            'courseDisplayName': self.course_display_name,
            'createdAt': to_isoformat(self.created_at),
            'instructorUids': self.instructor_uids,
            'kalturaScheduleId': self.kaltura_schedule_id,
            'meetingDays': formatted_days,
            'meetingDaysNames': get_names_of_days(formatted_days),
            'meetingEndDate': datetime.strftime(self.meeting_end_date, '%Y-%m-%d'),
            'meetingEndTime': self.meeting_end_time,
            'meetingEndTimeFormatted': format_time(self.meeting_end_time),
            'meetingStartDate': datetime.strftime(self.meeting_start_date, '%Y-%m-%d'),
            'meetingStartTime': self.meeting_start_time,
            'meetingStartTimeFormatted': format_time(self.meeting_start_time),
            'publishType': self.publish_type,
            'publishTypeName': NAMES_PER_PUBLISH_TYPE[self.publish_type],
            'recordingType': self.recording_type,
            'recordingTypeName': NAMES_PER_RECORDING_TYPE[self.recording_type],
            'room': room_feed,
            'sectionId': self.section_id,
            'termId': self.term_id,
        }
