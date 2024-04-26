import streamlit as st
from aied_functions.ac_sections import sections_single_call, sections_mass_call
from aied_functions.ac_activities import activities_single_call, activities_mass_call
from aied_functions.ac_components import components_single_call, components_mass_call
import streamlit_antd_components as sac
import configparser
import ast

class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

	def get_config_values(self, section, key):
		value = self.config.get(section, key)
		try:
			# Try converting the string value to a Python data structure
			return ast.literal_eval(value)
		except (SyntaxError, ValueError):
			# If not a data structure, return the plain string
			return value

config_handler = ConfigHandler()

SA =  config_handler.get_config_values('constants', 'SA')
AD =  config_handler.get_config_values('constants', 'AD')
BULK_TESTER = config_handler.get_config_values('constants', 'BULK_TESTER')
NORMAL_TESTER = config_handler.get_config_values('constants', 'NORMAL_TESTER')
RUBRICS = config_handler.get_config_values('Prompt_Design_Templates', 'RUBRICS')
SUBJECTS = config_handler.get_config_values('menu_lists', 'SUBJECTS_SINGAPORE')
LEVELS = config_handler.get_config_values('menu_lists', 'CLASS_LEVELS_SINGAPORE')
DEFAULT_LESSON_TAGS = 'Algebra, Geometry'
DEFAULT_LESSON_TITLE = 'Introduction to Algebra'
DEFAULT_LESSON_NOTES = 'This lesson covers the basics of algebraic expressions and equations.'
DEFAULT_ADDITIONAL_PROMPTS = 'Include hands-on activities and real-life examples'
DEFAULT_NUMBER_OF_SECTIONS = 3
AC_MODEL_LIST = config_handler.get_config_values('menu_lists', 'AC_MODEL_LIST')

def chatbot_settings():
	temp = st.number_input("Temperature", value=st.session_state.default_temp, min_value=0.0, max_value=1.0, step=0.1)
	presence_penalty = st.number_input("Presence Penalty", value=st.session_state.default_presence_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	frequency_penalty = st.number_input("Frequency Penalty", value=st.session_state.default_frequency_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	top_p = st.number_input("Top P", value=st.session_state.default_top_p, min_value=0.0, max_value=1.0, step=0.1)
	max_tokens = st.number_input("Max Tokens", value=st.session_state.default_max_tokens, min_value=0, max_value=4000, step=10)

	if st.button("Update Chatbot Settings", key = 3):
		st.session_state.default_temp = temp
		st.session_state.default_presence_penalty = presence_penalty
		st.session_state.default_frequency_penalty = frequency_penalty
		st.session_state.default_top_p = top_p
		st.session_state.default_max_tokens = max_tokens
  
def ac_co_pilot():
	options = sac.chip(items=[
									sac.ChipItem(label='Sections Single Call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Sections Mass Call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Activities Single Call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Activities Mass Call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Components Single (JSON)', icon='code-slash'),
									sac.ChipItem(label='Components Mass Call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Authoring Co-Pilot Framework', icon='body-text'),
								], index=[0],format_func='title', radius='sm', size='sm', align='left', variant='light')
 
	if options == 'Sections Single Call (JSON)':
		with st.expander("Chatbot Settings"):
			st.session_state.default_temp = 0.7
			chatbot_settings()
		sections_single_call()
	elif options == 'Sections Mass Call (JSON)':
		if st.session_state.user["profile_id"] == SA or st.session_state.user["profile_id"] == AD or st.session_state.user["profile_id"] == BULK_TESTER:
			with st.expander("Chatbot Settings"):
				st.session_state.default_temp = 0.7
				chatbot_settings()
			sections_mass_call()
		else:
			st.warning("You are not authorized to access this feature.")
	elif options == 'Activities Single Call (JSON)':
		with st.expander("Chatbot Settings"):
			st.session_state.default_temp = 0.7
			chatbot_settings()
		activities_single_call()
		pass
	elif options == 'Activities Mass Call (JSON)':
		#st.write("Activities Mass Call (JSON) is under development.")
		if st.session_state.user["profile_id"] == SA or st.session_state.user["profile_id"] == AD or st.session_state.user["profile_id"] == BULK_TESTER:
			with st.expander("Chatbot Settings"):
				st.session_state.default_temp = 0.7
				chatbot_settings()
			activities_mass_call()
		else:
			st.warning("You are not authorized to access this feature.")	
		pass
	elif options == 'Components Single (JSON)':
		with st.expander("Chatbot Settings"):
			st.session_state.default_temp = 0.7
			chatbot_settings()
		components_single_call()
		pass
	elif options == 'Components Mass Call (JSON)':
		#st.write("Activities Mass Call (JSON) is under development.")
		if st.session_state.user["profile_id"] == SA or st.session_state.user["profile_id"] == AD or st.session_state.user["profile_id"] == BULK_TESTER:
			with st.expander("Chatbot Settings"):
				st.session_state.default_temp = 0.7
				chatbot_settings()
			components_mass_call()
		#activities_mass_call()
		else:
			st.warning("You are not authorized to access this feature.")
		pass
	elif options == 'Authoring Co-Pilot Framework':
		#authoring_co_pilot()
		st.write("Authoring Co-Pilot Framework is under development.")
		pass




