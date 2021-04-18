from flask_wtf import FlaskForm
from wtforms.fields.html5 import URLField
from wtforms import StringField, BooleanField, SubmitField, IntegerField, SelectMultipleField, HiddenField, RadioField, SelectField
from wtforms.validators import DataRequired

class SocketAssignmentForm(FlaskForm):
    remote = HiddenField('Remote')
    socket = HiddenField('Socket')
    name = StringField('Name')
    category = StringField('Kategorie')
    timer_switch = BooleanField('Zeitschaltuhr')
    start = StringField('Von', render_kw={"placeholder": "hh:mm"})
    end = StringField('Bis', render_kw={"placeholder": "hh:mm"})
    monday = BooleanField('Mo.')
    tuesday = BooleanField('Di.')
    wednesday = BooleanField('Mi.')
    thursday = BooleanField('Do.')
    friday = BooleanField('Fr.')
    saturday = BooleanField('Sa.')
    sunday = BooleanField('So.')
    auto_off = BooleanField('Auto Off')
    auto_off_at = StringField('Um', render_kw={"placeholder": "hh:mm"})

class AudioOutputForm(FlaskForm):
    audio_output = RadioField(choices=[('hdmi', 'HDMI'), ('box', 'Boxen'), ('auto', 'Auto'), ('bt_bose', 'BT Bose'), ('bt_anker', 'BT Anker')])


class RadioSettingsForm(FlaskForm):
	name = StringField('Name')
	url = URLField('URL')

class RadioSelectionForm(FlaskForm):
	radio = SelectField('Name', coerce=str)
