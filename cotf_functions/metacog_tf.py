import streamlit as st
from aied_functions.ac_sections import sections_single_call, sections_mass_call
from aied_functions.ac_activities import activities_single_call, activities_mass_call
from aied_functions.ac_components import components_single_call, components_mass_call
import streamlit_antd_components as sac
import configparser
import ast
from basecode2.chatbot import openai_bot

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

CHATBOT = config_handler.get_config_values('constants', 'CHATBOT')

def tf_chatbot_functions():
#check if prompt_template is in session state the default is the chatbot_key
	CHATBOT = "Thinking Facilitator"
	chat_bot = "gpt-4-turbo-preview"
	memory = True
	rag = False
	st.session_state.chatbot = st.session_state.thinking_facilitator_prompt

	if st.button("Clear Chat"):
		clear_session_states()
		st.rerun()
			
	openai_bot(CHATBOT, chat_bot, memory, rag)

def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]
