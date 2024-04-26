import streamlit as st
from aied_functions.ac_sections import sections_single_call, sections_mass_call
from aied_functions.ac_activities import activities_single_call, activities_mass_call
from aied_functions.ac_components import components_single_call, components_mass_call
import streamlit_antd_components as sac
import configparser
import ast
from openai import OpenAI
from basecode2.chatbot import openai_bot, prompt_template_function, insert_into_data_table
from basecode2.authenticate import return_openai_key
from datetime import datetime

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

def metacog_feedback():
    placeholder = st.empty()

    with placeholder:
        inputs = {}
        inputs["question"] = ""
        inputs["text"] = ""

        with st.form("Metacognitive Feedback"):
            question = st.text_input("Question")
            text = st.text_area("Text for analysis")

            submitted = st.form_submit_button("Submit text for feedback")

            if submitted:
                inputs["question"] = question
                inputs["text"] = text
            
    if st.session_state.vs == False:
        st.warning("Metacognitive Feedback is not linked to any knowledge base")
    
    if inputs is not None:
        if inputs["text"] != "" and inputs["question"] != "":
            CHATBOT = "Metacognitive Feedback"
            chat_bot = "gpt-4-turbo-preview"
            memory = False
            rag = False 
            openai_API(inputs, CHATBOT, chat_bot, memory, rag)
        else:
            st.warning("You will need to enter both question and text.")

def openai_API(inputs, bot_name, model, memory, rag):
    client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=return_openai_key()	
    )
    # print(st.session_state.chatbot)
    prompt = "question: " + inputs['question'] + ", text: " + inputs['text']
    
    stream = client.chat.completions.create(
		model=model,
		messages=[
			{"role": "system", "content":st.session_state.metacognitive_feedback_prompt},
			{"role": "user", "content": prompt},
		],
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		stream=True #settings option
	)
    response = st.write_stream(stream)

    st.session_state.msg.append({"role": "assistant", "content": response})
	# Insert data into the table
    now = datetime.now() # Using ISO format for date
    num_tokens = len(str(response) + prompt)*1.3
    insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  response, prompt, num_tokens, bot_name)

        
            
    