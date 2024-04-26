import openai
from openai import OpenAI
import streamlit as st
from datetime import datetime
from basecode2.authenticate import return_openai_key, return_claude_key
import os
import streamlit_antd_components as sac
from html.parser import HTMLParser
import configparser
import ast
import pandas as pd
import json
import anthropic
from html import unescape

import re

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

RUBRICS = config_handler.get_config_values('Prompt_Design_Templates', 'RUBRICS')
SUBJECTS = config_handler.get_config_values('menu_lists', 'SUBJECTS_SINGAPORE')
LEVELS = config_handler.get_config_values('menu_lists', 'CLASS_LEVELS_SINGAPORE')
DEFAULT_SECTION_TAGS = 'Algebra, Geometry'
DEFAULT_ACTIVITY_TITLE = 'How to calculate critical angle'
DEFAULT_ACTIVITY_NOTES = """Introduce the concept of critical angle in the content of total internal reflection. 
Use visuals such as simulations and ray diagram to illustrate how to derive the critical angle from first principles using Snell’s Law."""
DEFAULT_ADDITIONAL_PROMPTS = """For example, students should have the opportunity to try a hands-on activity to learn this concept. 
The hands-on activity should get students to be able to derive the formula to calculate the critical angle from first principles. 
Scaffolded activities can first allow students to fill in the blanks to demonstrate their understanding of how apply Snell’s Law to calculate critical angle, 
second get students to calculate critical angle as a free response question without scaffolds. Allow students to use their calculator on their own"""
DEFAULT_NUMBER_OF_COMPONENTS= 3
DURATION = "1 hours 30 minutes 30 seconds"
KNOWLEDGE_BASE = """
Snell’s Law, critical angle
Educational content is designed to foster critical thinking, problem-solving skills, and a deep understanding of subject matter. 
Effective lesson plans engage students through interactive activities, discussions, and practical applications of theoretical concepts. 
Assessment strategies should be varied and aligned with learning outcomes to accurately measure student understanding and progress. 
Incorporating technology and real-world examples into the curriculum enhances learning experiences and prepares students for future challenges.
"""
AC_MODEL_LIST = config_handler.get_config_values('menu_lists', 'AC_MODEL_LIST')

def get_and_display_duration():
	# Default duration values
	#default_hours, default_minutes, default_seconds = DURATION.split()

	# Splitting the default duration values to extract integers
	default_hours = 1 # Extracts '1' from '1 hours'
	default_minutes = 30  # Extracts '30' from '30 minutes'
	default_seconds = 0  # Extracts '30' from '30 seconds'

	d1, d2, d3, d4 = st.columns([1, 1, 1, 5])
	# User inputs for hours, minutes, seconds
	with d1:
		hours = st.number_input("Hours:", min_value=0, value=default_hours, format="%d")
	with d2:
		minutes = st.number_input("Minutes:", min_value=0, value=default_minutes, max_value=59, format="%d")
	with d3:
		seconds = st.number_input("Seconds:", min_value=0, value=default_seconds, max_value=59, format="%d")
	with d4:
		pass
 
	# Formatting the duration string
	duration_formatted = f"{hours} hours {minutes} minutes {seconds} seconds"

	# Storing the formatted duration in session state
	st.session_state.activity_duration = duration_formatted

	# Optionally, display the formatted string
	st.write("Duration:", duration_formatted)


def components_single_call():
	# Initialize default values if not already set
	if 'level' not in st.session_state:
		st.session_state.level = LEVELS[0]
	if 'subject' not in st.session_state:
		st.session_state.subject = SUBJECTS[0]
	# Set default values for SECTION details if not already set
	if 'section_tags' not in st.session_state:
		st.session_state.section_tags = DEFAULT_SECTION_TAGS
	if 'activity_title' not in st.session_state:
		st.session_state.activity_title = DEFAULT_ACTIVITY_TITLE
	if 'activity_notes' not in st.session_state:
		st.session_state.activity_notes = DEFAULT_ACTIVITY_NOTES
	if 'activity_duration' not in st.session_state:
		st.session_state.activity_duration = DURATION
	if 'component_additional_prompts' not in st.session_state:
		st.session_state.component_additional_prompts = DEFAULT_ADDITIONAL_PROMPTS
	if 'number_of_components' not in st.session_state:
		st.session_state.number_of_components = DEFAULT_NUMBER_OF_COMPONENTS
	if 'knowledge_base' not in st.session_state:
		st.session_state.knowledge_base = KNOWLEDGE_BASE
	

	# UI for section generation
	c1, c2, c3 = st.columns([1, 1, 3])
	st.write("### Components generation")
	with c1:
		level = st.selectbox("Select your level:", options=LEVELS, index=0)
		st.session_state.level = level
	with c2:
		subject = st.selectbox("Select your subject:", options=SUBJECTS, index=0)
		st.session_state.subject = subject
	#need to change below
	st.session_state.section_tags  = st.text_input("Enter Section Tags (Learning Objectives):", value=st.session_state.section_tags)
	st.session_state.activity_title = st.text_input("Activity Title:", value=st.session_state.activity_title)
	st.session_state.activity_notes = st.text_area("Activity Notes:", value=st.session_state.activity_notes, height=300)
	st.session_state.component_additional_prompts = st.text_area("Additional Prompts/Instructions:", value=st.session_state.component_additional_prompts, height=300)
	st.session_state.knowledge_base = st.text_area("Knowledge Base:", value=st.session_state.knowledge_base, height=300)
	get_and_display_duration()
	st.session_state.number_of_components = st.number_input("Number of Components:", min_value=1, value=st.session_state.number_of_components)
 
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)
 	# Button to confirm and potentially generate the section sections
	if model != "-":
		if model.startswith("gpt"):
			generate_component_openai(model)
		elif model.startswith("claude"):
			generate_component_claude(model)
   
def generate_component_claude(model):
	if "claude_prompt" not in st.session_state:
		st.session_state.claude_prompt = ""
	# Constructing the prompt from the session state
	template = ("As an experienced {Level} {Subject} teacher, design components for an activity or quiz that helps students achieve the following learning outcomes:\n {Section_Tags}\n  \n "
				"The title of the activity is {Activity_Title} and brief notes are {Activity_Notes}.\n"
				"You should also consider: {Additional_Prompts}.\n Students are expected to spend {Duration} on this activity or quiz."
				"Suggest {Number_of_Components} components for this activity or quiz. The components should be based on the information in {Knowledge_Base}.\n"
				"There are only five types of components:\n"
				"1. A paragraph of text to help students understand the learning outcomes. The text can include explanations and examples to make it easier for students to understand the learning outcomes.\n"
				"2. A multiple choice question with four options of which only one option is correct\n"
				"3. A free response question which includes suggested answers\n"
				"4. A poll which is a multiple choice question with four options but no correct answer\n"
				"5. A discussion question which invites students to respond with their opinion\n Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml.\n"
				"Your output should be a maximum of twelve components.\n"
				"The first component is an activity description that describes the activity to the student.\n"
				"The second component should be instructions to students on how to complete the activity.\n The rest of the components can be either text, multiple choice question, free response question, poll or discussion question.\n"
				"For each paragraph of text, provide (i) the required text, which can include tables or lists.\n For each multiple choice question, provide (i) the question, (ii) one correct answer, (iii) feedback for why the correct answer answers the question (iv) three distractors which are incorrect answers, (v) feedback for each distractor explaining why the distractor is incorrect and what the correct answer should be (vi) suggested time needed for a student to complete the question.\n"
				"For each free response question, provide (i) the question, (ii) total marks for the question, (iii) suggested answer, which is a comprehensive list of creditworthy points, where one point is to be awarded one mark, up to the total marks for the question, (iv) suggested time needed for a student to complete the question.\n"
				"For each poll, provide (i) a question, (ii) at least two options in response to the question.\n For each discussion question, provide (i) the discussion topic, (ii) a free response question for students to respond to."
				)
 
	prompt_options = {
			"AC Claude Component Production Prompt": st.session_state.ac_claude_component_production_prompt,
			"AC Claude Component Development Prompt 1": st.session_state.ac_claude_component_development_prompt_1,
			"AC Claude Component Development Prompt 2": st.session_state.ac_claude_component_development_prompt_2,
		}

	# Let the user select a prompt by name
	selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

	# Set the select_prompt to the corresponding session state value based on the selected name
	select_prompt = prompt_options[selected_prompt_name]
 
	if st.checkbox("Load Claude Sample Prompt", key="c_prompt"):
		select_prompt = template

	# Display the selected prompt
	st.write(select_prompt)
	
	
	formatted_prompt = template.format(
		Level=st.session_state.get('level', 'Level'),
		Subject=st.session_state.get('subject', 'Subject'),
		Section_Tags=st.session_state.get('section_tags', 'Section_Tags'),
		Activity_Title=st.session_state.get('activity_title', 'Activity_Title'),  # Changed key to Activity_Title
		Activity_Notes=st.session_state.get('activity_notes', 'Activity_Notes'),  # Changed key to Activity_Notes
		Additional_Prompts=st.session_state.get('component_additional_prompts', 'Additional_Prompts'),
		Duration=st.session_state.get('activity_duration', 'Duration'),
		Number_of_Components=st.session_state.get('number_of_components', 'Number_of_Components'),  # Changed key to Number_of_Components
		Knowledge_Base=st.session_state.get('knowledge_base', 'Knowledge_Base')
	)

	# Here, you would call the Claude API with the formatted prompt
	# For simulation, let's format a JSON response as described and store it in session state
	example_response = {
		"recommendations": {
			"activityRecommendation": {
				"activityDescription": {
					"richtext": "<p>Description</p>"
				},
				"activityInstruction": {
					"richtext": "<p>Instruction</p>"
				}
			},
			"componentRecommendations": [
				{
					"text": {
						"richtext": "<p>text content</p>"
					}
				},
				{
					"multipleChoiceQuestion": {
						"question": {
							"richtext": "<p>question content</p>"
						},
						"answers": [
							{
								"richtext": "<p>answer</p>"
							}
						],
						"distractors": [
							{
								"richtext": "<p>distractor 1</p>"
							},
							{
								"richtext": "<p>distractor 2</p>"
							},
							{
								"richtext": "<p>distractor 3</p>"
							}
						],
						"duration": 60,
						"totalMarks": 1
					}
				},
				{
					"freeResponseQuestion": {
						"question": {
							"richtext": "<p>question content</p>"
						},
						"totalMarks": 5,
						"duration": 120
					}
				},
				{
					"poll": {
						"question": {
							"richtext": "<p>poll content</p>"
						},
						"options": [
							{
								"richtext": "<p>option 1</p>"
							},
							{
								"richtext": "<p>option 2</p>"
							},
							{
								"richtext": "<p>option 3</p>"
							}
						]
					}
				},
				{
					"discussionQuestion": {
						"topic": "disucssion topic",
						"question": {
							"richtext": "<p>discussion content</p>"
						}
					}
				}
			]
		}
	}


	
	
	
	editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


	# Convert the example response to JSON string for demonstration
	#json_response = json.dumps(example_response, indent=4)
	
	json_response = st.session_state.ac_claude_component_example_prompt
  
	if st.checkbox("Load Claude Example JSON", key="claude_tools"):
		json_response = json.dumps(example_response, indent=4)
 
	# Display the formatted prompt in Streamlit for demonstration purposes
	appended_prompt = editable_prompt + "  Return the response in JSON format. Here is an example of ideal formatting for the JSON recommendation: \n" + json_response

	st.write(f":blue[Full claude API prompt]:")
	st.write(f"{appended_prompt}")
	# Normally, you would replace the example_response with the actual API response
	# For demonstration, we'll update the session state with the example JSON response
	if st.button("Generate Activities"):
		start_time = datetime.now() 
		with st.status("Generating Activities..."):
			st.session_state.claude_prompt = appended_prompt
			client = anthropic.Anthropic(api_key=return_claude_key())
			message = client.messages.create(
			model=model,
			max_tokens=st.session_state.default_max_tokens,
			top_p=st.session_state.default_top_p,
			temperature=st.session_state.default_temp,
			messages=[
				{
					"role": "user", 
					"content": appended_prompt
				},
			]
			) #.content[0].text
			st.write(message) #break it down into parts
			display_lesson_from_json_claude(message, st.session_state.number_of_components)
			end_time = datetime.now()  # Capture the end time after processing
			duration = (end_time - start_time).total_seconds()  # Calculate duration in seconds
			st.write(f"Processing time: {duration} seconds")
	
	# Display the JSON formatted response in Streamlit for demonstration purposes


# class MLStripper(HTMLParser):
# 	def __init__(self):
# 		super().__init__()
# 		self.reset()
# 		self.strict = False
# 		self.convert_charrefs= True
# 		self.text = []
# 	def handle_data(self, d):
# 		self.text.append(d)
# 	def get_data(self):
# 		return ''.join(self.text)

# def clean_html_tags(html):
# 	s = MLStripper()
# 	s.feed(html)
# 	return s.get_data()

# def escape_json_string(json_string):
# 	"""Escape unescaped control characters in a JSON string."""
# 	json_string = json_string.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
# 	return json_string

# def ensure_proper_json_format(json_string):
# 	"""Attempts to ensure that JSON string is properly formatted."""
# 	try:
# 		json.loads(json_string)  # Try parsing the original JSON string
# 		return json_string
# 	except json.JSONDecodeError as initial_error:
# 		st.write("Initial JSON parsing error:", initial_error)

# 		# Clean and correct the JSON string
# 		# Strip unnecessary spaces, escape control characters, and ensure quotes are corrected
# 		corrected_json_string = escape_json_string(json_string) # Replace single quotes
# 		corrected_json_string = re.sub(r'([{,]\s*)(\w+)(\s*:\s*)', r'\1"\2"\3', corrected_json_string)

# 		try:
# 			# Try parsing again with corrected JSON
# 			json.loads(corrected_json_string)
# 			return corrected_json_string
# 		except json.JSONDecodeError as corrected_error:
# 			st.write("Corrected JSON parsing error:", corrected_error)
# 			st.write("Corrected JSON string:", corrected_json_string)
# 			raise ValueError(f"JSON data is still not properly formatted: {corrected_error}")


# # def ensure_proper_json_format(json_string):
# #     """Ensures that the JSON string uses double quotes for keys and values."""
# #     try:
# #         # This attempts to parse the JSON to check its validity.
# #         json.loads(json_string)
# #         return json_string
# #     except json.JSONDecodeError:
# #         # If it fails, replace single quotes with double quotes and recheck
# #         corrected_json_string = json_string.replace("'", '"')
# #         corrected_json_string =  escape_json_string(corrected_json_string)
# #         try:
# #             json.loads(corrected_json_string)
# #             return corrected_json_string
# #         except json.JSONDecodeError as e:
# #             raise ValueError(f"JSON data is not properly formatted: {e}")

# def display_lesson_from_json_claude(message_object, expected_component_count):
# 	try:
# 		if hasattr(message_object, 'content') and isinstance(message_object.content, list) and isinstance(message_object.content[0].text, str):
# 			raw_json_string = message_object.content[0].text
# 			raw_json_string = raw_json_string.replace('<recommendation>', '').replace('</recommendation>', '')
# 			# Ensure JSON format is correct
# 			raw_json_string = ensure_proper_json_format(raw_json_string)
# 		else:
# 			raise ValueError("Invalid message format. Cannot find the JSON content.")

# 		message_data = json.loads(raw_json_string)
		
# 		recommendations = message_data.get('recommendations', {})
		
# 		# Display Activity Recommendation
# 		activity_recommendation = recommendations.get('activityRecommendation', {})
# 		st.subheader("Activity Description:")
# 		st.write(clean_html_tags(activity_recommendation.get('activityDescription', {}).get('richtext', 'No description provided')))
# 		st.subheader("Activity Instruction:")
# 		st.write(clean_html_tags(activity_recommendation.get('activityInstruction', {}).get('richtext', 'No instructions provided')))
		
# 		# Display Component Recommendations
# 		component_recommendations = recommendations.get('componentRecommendations', [])
# 		actual_component_count = len(component_recommendations)
# 		if actual_component_count != expected_component_count:
# 			st.warning(f"Expected {expected_component_count} components, but found {actual_component_count}.")
# 		else:
# 			st.success(f"Number of components matches the expected count: {expected_component_count}.")

# 		for component in component_recommendations:
# 			if 'text' in component:
# 				st.subheader("Text Content:")
# 				st.write(clean_html_tags(component['text'].get('richtext', 'No text provided')))
# 			elif 'multipleChoiceQuestion' in component:
# 				process_multiple_choice_question(component)
# 			elif 'freeResponseQuestion' in component:
# 				process_free_response_question(component)
# 			elif 'poll' in component:
# 				process_poll(component)
# 			elif 'discussionQuestion' in component:
# 				process_discussion_question(component)

# 	except Exception as e:
# 		st.error(f"Error processing the lesson content: {e}")
	



def process_multiple_choice_question(component):
	mcq = component['multipleChoiceQuestion']
	st.subheader("Multiple Choice Question:")
	st.write(clean_html_tags(mcq.get('question', {}).get('richtext', 'No question provided')))
	st.write(f"Duration: {mcq.get('duration')} seconds")
	st.write(f"Total Marks: {mcq.get('totalMarks')}")
	st.write("Answers:")
	for answer in mcq.get('answers', []):
		st.write(clean_html_tags(answer.get('richtext', 'No answer provided')))
	st.write("Distractors:")
	for distractor in mcq.get('distractors', []):
		st.write(clean_html_tags(distractor.get('richtext', 'No distractor provided')))

def process_free_response_question(component):
	frq = component['freeResponseQuestion']
	st.subheader("Free Response Question:")
	# Display the question, ensuring any HTML tags are cleaned.
	st.write(clean_html_tags(frq.get('question', {}).get('richtext', 'No question provided')))
	st.write(f"Duration: {frq.get('duration')} seconds")
	st.write(f"Total Marks: {frq.get('totalMarks')}")

	# Check if 'suggestedAnswer' exists in FRQ component
	if 'suggestedAnswer' in frq:
		st.write("Suggested Answer:")
		suggested_answers = frq['suggestedAnswer']
		# Check if suggested answers are a list of strings or contain more complex structures
		if suggested_answers and isinstance(suggested_answers[0], dict):
			# If the suggested answers are dictionaries, possibly with 'richtext'
			for answer in suggested_answers:
				st.write(clean_html_tags(answer.get('richtext', '')))
		else:
			# If the suggested answers are just strings
			for answer in suggested_answers:
				st.write(clean_html_tags(answer))


def process_poll(component):
	poll = component['poll']
	st.subheader("Poll Question:")
	st.write(clean_html_tags(poll.get('question', {}).get('richtext', 'No poll question provided')))
	st.write("Options:")
	for option in poll.get('options', []):
		st.write(clean_html_tags(option.get('richtext', 'No option provided')))

def process_discussion_question(component):
	dq = component['discussionQuestion']
	st.subheader("Discussion Topic:")
	st.write(dq.get('topic', 'No topic provided'))
	st.subheader("Discussion Question:")
	st.write(clean_html_tags(dq.get('question', {}).get('richtext', 'No discussion question provided')))



class MLStripper(HTMLParser):
	def __init__(self):
		super().__init__()
		self.reset()
		self.strict = False
		self.convert_charrefs= True
		self.text = []
	def handle_data(self, d):
		self.text.append(d)
	def get_data(self):
		return ''.join(self.text)


def clean_html_tags(html):
	s = MLStripper()
	s.feed(html)
	return s.get_data()

def display_lesson_from_json_claude(message_object, expected_component_count):
	try:
		# Parse the JSON string from the message content
		# Assuming message_object.content is a list with at least one item, and that item has a 'text' attribute
		if hasattr(message_object, 'content') and isinstance(message_object.content, list):
			raw_json_string = message_object.content[0].text
			raw_json_string = raw_json_string.replace('<recommendation>', '').replace('</recommendation>', '')
		else:
			raise ValueError("Invalid message format. Cannot find the JSON content.")
		message_data = json.loads(raw_json_string)
		
		recommendations = message_data.get('recommendations', {})
		
		# Display Activity Recommendation
		activity_recommendation = recommendations.get('activityRecommendation', {})
		st.subheader("Activity Description:")
		st.write(clean_html_tags(activity_recommendation.get('activityDescription', {}).get('richtext', 'No description provided')))
		st.subheader("Activity Instruction:")
		st.write(clean_html_tags(activity_recommendation.get('activityInstruction', {}).get('richtext', 'No instructions provided')))
		
		# Display Component Recommendations
		component_recommendations = recommendations.get('componentRecommendations', [])
		actual_component_count = len(component_recommendations)
		if actual_component_count != expected_component_count:
			st.warning(f"Expected {expected_component_count} components, but found {actual_component_count}.")
		else:
			st.success(f"Number of components matches the expected count: {expected_component_count}.")
   
		for component in component_recommendations:
			if 'text' in component:
				st.subheader("Text Content:")
				st.write(clean_html_tags(component['text'].get('richtext', 'No text provided')))
			elif 'multipleChoiceQuestion' in component:
				process_multiple_choice_question(component)
			elif 'freeResponseQuestion' in component:
				process_free_response_question(component)
			elif 'poll' in component:
				process_poll(component)
			elif 'discussionQuestion' in component:
				process_discussion_question(component)

	except Exception as e:
		st.error(f"Error processing the lesson content: {e}")



#ned to mod below
#openai ============================================================================
def generate_component_openai(model):
	if 'openai_prompt' not in st.session_state:
		st.session_state.openai_prompt = ""

	# Template with placeholders
	template =  ("As an experienced {Level} {Subject} teacher, design components for an activity or quiz that helps students achieve the following learning outcomes:\n {Section_Tags}\n  \n "
				"The title of the activity is {Activity_Title} and brief notes are {Activity_Notes}.\n"
				"You should also consider: {Additional_Prompts}.\n Students are expected to spend {Duration} on this activity or quiz."
				"Suggest {Number_of_Components} components for this activity or quiz. The components should be based on the information in {Knowledge_Base}.\n"
				"There are only five types of components:\n"
				"1. A paragraph of text to help students understand the learning outcomes. The text can include explanations and examples to make it easier for students to understand the learning outcomes.\n"
				"2. A multiple choice question with four options of which only one option is correct\n"
				"3. A free response question which includes suggested answers\n"
				"4. A poll which is a multiple choice question with four options but no correct answer\n"
				"5. A discussion question which invites students to respond with their opinion\n Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml.\n"
				"Your output should be a maximum of twelve components.\n"
				"The first component is an activity description that describes the activity to the student.\n"
				"The second component should be instructions to students on how to complete the activity.\n The rest of the components can be either text, multiple choice question, free response question, poll or discussion question.\n"
				"For each paragraph of text, provide (i) the required text, which can include tables or lists.\n For each multiple choice question, provide (i) the question, (ii) one correct answer, (iii) feedback for why the correct answer answers the question (iv) three distractors which are incorrect answers, (v) feedback for each distractor explaining why the distractor is incorrect and what the correct answer should be (vi) suggested time needed for a student to complete the question.\n"
				"For each free response question, provide (i) the question, (ii) total marks for the question, (iii) suggested answer, which is a comprehensive list of creditworthy points, where one point is to be awarded one mark, up to the total marks for the question, (iv) suggested time needed for a student to complete the question.\n"
				"For each poll, provide (i) a question, (ii) at least two options in response to the question.\n For each discussion question, provide (i) the discussion topic, (ii) a free response question for students to respond to."
				)
	
	prompt_options = {
		"AC OpenAI Component Production Prompt": st.session_state.ac_openai_component_production_prompt,
		"AC OpenAI Component Development Prompt 1": st.session_state.ac_openai_component_development_prompt_1,
		"AC OpenAI Component Development Prompt 2": st.session_state.ac_openai_component_development_prompt_2,
	}

	# Let the user select a prompt by name
	selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

	# Set the select_prompt to the corresponding session state value based on the selected name
	select_prompt = prompt_options[selected_prompt_name]
 
	if st.checkbox("Load Sample Prompt"):
		select_prompt = template
	# Display the selected prompt
	st.write(select_prompt)
	
	
 
	json_tools = tool_function()
	tools = load_json(json_tools)
	
	# Formatting the template with actual session state values
	formatted_prompt = template.format(
		Level=st.session_state.get('level', 'Level'),
		Subject=st.session_state.get('subject', 'Subject'),
		Section_Tags=st.session_state.get('section_tags', 'Section_Tags'),
		Activity_Title=st.session_state.get('activity_title', 'Activity_Title'),  # Changed key to Activity_Title
		Activity_Notes=st.session_state.get('activity_notes', 'Activity_Notes'),  # Changed key to Activity_Notes
		Additional_Prompts=st.session_state.get('component_additional_prompts', 'Additional_Prompts'),
		Duration=st.session_state.get('activity_duration', 'Duration'),
		Number_of_Components=st.session_state.get('number_of_components', 'Number_of_Components'),  # Changed key to Number_of_Components
		Knowledge_Base=st.session_state.get('knowledge_base', 'Knowledge_Base')
	)
	
	st.session_state.openai_prompt = formatted_prompt
	# Display the formatted prompt in Streamlit (for demonstration purposes)
	edited_prompt = st.text_area("Generated Prompt", value=st.session_state.openai_prompt, height=300)
	
	if st.button("Generate Components"):
		# Update the session state with the formatted prompt
		start_time = datetime.now()
		st.session_state.openai_prompt = edited_prompt
		client = OpenAI(
		# defaults to os.environ.get("OPENAI_API_KEY")
		api_key=return_openai_key()	
		)
		#openai.api_key = return_openai_key()
		#os.environ["OPENAI_API_KEY"] = return_openai_key()
		#st.title("Api Call with JSON")
		#MODEL = "gpt-3.5-turbo"
		with st.status("Calling the OpenAI API..."):
			response = client.chat.completions.create(
				model=model,
				messages=[
				#{"role": "system", "content": "You are a helpful assistant designed to output JSON."}, #system prompt
				{"role": "user", "content": edited_prompt},
				],
				#response_format={ "type": "json_object" }, #response format
				tools = tools,
				tool_choice = {"type": "function", "function": {"name": "get_new_component_recommendations"}},
				temperature=st.session_state.default_temp, #settings option
				presence_penalty=st.session_state.default_presence_penalty, #settings option
				frequency_penalty=st.session_state.default_frequency_penalty, #settings option
				top_p = st.session_state.default_top_p, #settings option
				max_tokens=st.session_state.default_max_tokens, #settings option
			)
			st.markdown("**This is the extracted response:**")
			st.write(response)
			display_lesson_from_json_openai(response, st.session_state.number_of_components)
			end_time = datetime.now()  # Capture the end time after processing
			duration = (end_time - start_time).total_seconds()  # Calculate duration in seconds
			st.write(f"Processing time: {duration} seconds")


def load_json(json_tools):
	try:
		# Assuming json_tools is a string variable containing your JSON data
		tools = json.loads(json_tools)
		return tools
		# Proceed with your logic using the 'tools' dictionary
	except json.JSONDecodeError:
		# Use Streamlit's error messaging to inform the user
		st.error("Error: The input provided is not valid JSON. Please ensure you input a valid JSON text.")
		st.stop()
	except Exception as e:
		# For other exceptions, you might still want to log them or inform the user
		st.error(f"An unexpected error occurred: {e}")
		st.stop()


def tool_function():
	
	st.write(":red[Functional tools for OpenAI JSON API call:]")

	# if "j_tools_format" not in st.session_state:
	# 	st.session_state.j_tools_format = st.session_state.ac_openai_tools_section_production_prompt

	# Create a mapping between format names and their corresponding session state values
	tools_format_options = {
		"AC OpenAI Tools Component Production Prompt": st.session_state.ac_openai_tools_component_production_prompt,
		"AC OpenAI Tools Component Development Prompt 1": st.session_state.ac_openai_tools_component_development_prompt_1,
	}
	
	# Let the user select a tools format by name
	selected_format_name = st.selectbox("Select your functional tools format: (JSON)", tuple(tools_format_options.keys()))

	# Set the j_tools_format to the corresponding session state value based on the selected name
	j_tools_format = tools_format_options[selected_format_name]

	# Display the selected tools format in a text area for editing
	st.markdown(j_tools_format, unsafe_allow_html=True)
	st.divider()
	return j_tools_format

def display_lesson_from_json_openai(chat_completion_object, expected_sections_count):
	try:
		# Extracting the JSON string from the provided structure
		arguments_json = chat_completion_object.choices[0].message.tool_calls[0].function.arguments
		# Now, parse this JSON string to get the actual lesson content
		lesson_content = json.loads(arguments_json)
		
		recommendations = lesson_content.get('recommendations', {})
		
		# Display Activity Recommendation
		activity_recommendation = recommendations.get('activityRecommendation', {})
		st.subheader("Activity Description:")
		st.write(clean_html_tags(activity_recommendation.get('activityDescription', {}).get('richtext', 'No description provided')))
		st.subheader("Activity Instruction:")
		st.write(clean_html_tags(activity_recommendation.get('activityInstruction', {}).get('richtext', 'No instructions provided')))
		
		# Display Component Recommendations and count them
		component_recommendations = recommendations.get('componentRecommendations', [])
		actual_sections_count = len(component_recommendations)
		if actual_sections_count != expected_sections_count:
			st.warning(f"Expected {expected_sections_count} components, but found {actual_sections_count}.")
		else:
			st.success(f"Number of components matches the expected count: {expected_sections_count}.")
		
		for component in component_recommendations:
			if 'text' in component:
				st.subheader("Text Content:")
				st.write(clean_html_tags(component['text'].get('richtext', 'No text provided')))
			elif 'multipleChoiceQuestion' in component:
				mcq = component['multipleChoiceQuestion']
				st.subheader("Multiple Choice Question:")
				st.write(clean_html_tags(mcq.get('question', {}).get('richtext', 'No question provided')))
				 # Extract and display duration and totalMarks
				st.write(f"Duration: {mcq.get('duration')} seconds")
				st.write(f"Total Marks: {mcq.get('totalMarks')}")
				# Display answers and distractors
				st.write("Answers:")
				for answer in mcq.get('answers', []):
					st.write(clean_html_tags(answer.get('richtext', 'No answer provided')))
				st.write("Distractors:")
				for distractor in mcq.get('distractors', []):
					st.write(clean_html_tags(distractor.get('richtext', 'No distractor provided')))
			elif 'freeResponseQuestion' in component:
				frq = component['freeResponseQuestion']
				st.subheader("Free Response Question:")
				st.write(clean_html_tags(frq.get('question', {}).get('richtext', 'No question provided')))
				# Extract and display duration and totalMarks
				st.write(f"Duration: {frq.get('duration')} seconds")
				st.write(f"Total Marks: {frq.get('totalMarks')}")
				# Display suggested answer if available
				if 'suggestedAnswer' in frq:
					st.write("Suggested Answer:")
					for answer in frq.get('suggestedAnswer', []):
						st.write(clean_html_tags(answer.get('richtext', '')))
			elif 'poll' in component:
				poll = component['poll']
				st.subheader("Poll Question:")
				st.write(clean_html_tags(poll.get('question', {}).get('richtext', 'No poll question provided')))
				st.write("Options:")
				for option in poll.get('options', []):
					st.write(clean_html_tags(option.get('richtext', 'No option provided')))
			elif 'discussionQuestion' in component:
				dq = component['discussionQuestion']
				st.subheader("Discussion Topic:")
				st.write(dq.get('topic', 'No topic provided'))
				st.subheader("Discussion Question:")
				st.write(clean_html_tags(dq.get('question', {}).get('richtext', 'No discussion question provided')))
			
	except Exception as e:
		st.error(f"Error processing the lesson content: {e}")





#---------------------------------Mass API Call---------------------------------#	

def components_mass_call():
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)

	st.write("Mass API call JSON format: ")
	st.write(":red[Ensure your CSV file has the following columns: subject, level, section_tags, activity_title, activity_notes, additional_prompts, duration, number_of_components, knowledge_base]")
	if upload_csv():
		if st.button("Cancel Upload"):
			st.session_state.prompt_df = None
		pass_test = check_column_values(st.session_state.prompt_df , ["subject", "level", "section_tags", "activity_title", "activity_notes", "additional_prompts", "duration", "number_of_components", "knowledge_base"])
		if not pass_test:
			st.error("Please upload a CSV file with the required columns or modify the dataframe")
		if pass_test:
			if model != "-":
				batch_call(model)
	

def batch_call(model):
	
	template =  ("As an experienced {Level} {Subject} teacher, design components for an activity or quiz that helps students achieve the following learning outcomes:\n {Section_Tags}\n  \n "
			"The title of the activity is {Activity_Title} and brief notes are {Activity_Notes}.\n"
			"You should also consider: {Additional_Prompts}.\n Students are expected to spend {Duration} on this activity or quiz."
			"Suggest {Number_of_Components} components for this activity or quiz. The components should be based on the information in {Knowledge_Base}.\n"
			"There are only five types of components:\n"
			"1. A paragraph of text to help students understand the learning outcomes. The text can include explanations and examples to make it easier for students to understand the learning outcomes.\n"
			"2. A multiple choice question with four options of which only one option is correct\n"
			"3. A free response question which includes suggested answers\n"
			"4. A poll which is a multiple choice question with four options but no correct answer\n"
			"5. A discussion question which invites students to respond with their opinion\n Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml.\n"
			"Your output should be a maximum of twelve components.\n"
			"The first component is an activity description that describes the activity to the student.\n"
			"The second component should be instructions to students on how to complete the activity.\n The rest of the components can be either text, multiple choice question, free response question, poll or discussion question.\n"
			"For each paragraph of text, provide (i) the required text, which can include tables or lists.\n For each multiple choice question, provide (i) the question, (ii) one correct answer, (iii) feedback for why the correct answer answers the question (iv) three distractors which are incorrect answers, (v) feedback for each distractor explaining why the distractor is incorrect and what the correct answer should be (vi) suggested time needed for a student to complete the question.\n"
			"For each free response question, provide (i) the question, (ii) total marks for the question, (iii) suggested answer, which is a comprehensive list of creditworthy points, where one point is to be awarded one mark, up to the total marks for the question, (iv) suggested time needed for a student to complete the question.\n"
			"For each poll, provide (i) a question, (ii) at least two options in response to the question.\n For each discussion question, provide (i) the discussion topic, (ii) a free response question for students to respond to."
			)
	# Check if the model is selected	
	
	
	if model.startswith("gpt"):
	
		# Template with placeholders
		prompt_options = {
		"AC OpenAI Component Production Prompt": st.session_state.ac_openai_component_production_prompt,
		"AC OpenAI Component Development Prompt 1": st.session_state.ac_openai_component_development_prompt_1,
		"AC OpenAI Component Development Prompt 2": st.session_state.ac_openai_component_development_prompt_2,
		}

		# Let the user select a prompt by name
		selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

		# Set the select_prompt to the corresponding session state value based on the selected name
		select_prompt = prompt_options[selected_prompt_name]

		if st.checkbox("Load Sample Prompt"):
			select_prompt = template
		
  		# Display the selected prompt
		st.write(select_prompt)
	
		json_tools = tool_function()
		tools = load_json(json_tools)
	
	elif model.startswith("claude"):
		
 
		prompt_options = {
			"AC Claude Component Production Prompt": st.session_state.ac_claude_component_production_prompt,
			"AC Claude Component Development Prompt 1": st.session_state.ac_claude_component_development_prompt_1,
			"AC Claude Component Development Prompt 2": st.session_state.ac_claude_component_development_prompt_2,
		}
		# Let the user select a prompt by name
		selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

		# Set the select_prompt to the corresponding session state value based on the selected name
		select_prompt = prompt_options[selected_prompt_name]
	
		if st.checkbox("Load Claude Sample Prompt", key="c_prompt"):
			select_prompt = template

		# Display the selected prompt
		st.write(select_prompt)
	
		example_response = {
				"recommendations": {
					"activityRecommendation": {
						"activityDescription": {
							"richtext": "<p>Description</p>"
						},
						"activityInstruction": {
							"richtext": "<p>Instruction</p>"
						}
					},
					"componentRecommendations": [
						{
							"text": {
								"richtext": "<p>text content</p>"
							}
						},
						{
							"multipleChoiceQuestion": {
								"question": {
									"richtext": "<p>question content</p>"
								},
								"answers": [
									{
										"richtext": "<p>answer</p>"
									}
								],
								"distractors": [
									{
										"richtext": "<p>distractor 1</p>"
									},
									{
										"richtext": "<p>distractor 2</p>"
									},
									{
										"richtext": "<p>distractor 3</p>"
									}
								],
								"duration": 60,
								"totalMarks": 1
							}
						},
						{
							"freeResponseQuestion": {
								"question": {
									"richtext": "<p>question content</p>"
								},
								"totalMarks": 5,
								"duration": 120
							}
						},
						{
							"poll": {
								"question": {
									"richtext": "<p>poll content</p>"
								},
								"options": [
									{
										"richtext": "<p>option 1</p>"
									},
									{
										"richtext": "<p>option 2</p>"
									},
									{
										"richtext": "<p>option 3</p>"
									}
								]
							}
						},
						{
							"discussionQuestion": {
								"topic": "disucssion topic",
								"question": {
									"richtext": "<p>discussion content</p>"
								}
							}
						}
					]
				}
			}
		
		
		
		#editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


		# Convert the example response to JSON string for demonstration
		#json_response = json.dumps(example_response, indent=4)
		
		json_response = st.session_state.ac_claude_component_example_prompt
	
		if st.checkbox("Load Claude Example JSON", key="claude_tools"):
			json_response = json.dumps(example_response, indent=4)
	
		# Display the formatted prompt in Streamlit for demonstration purposes
		
	
	
	# Display the formatted prompt in Streamlit (for demonstration purposes)
 
	df = st.session_state.prompt_df

	if st.button("Execute Batch Call"):
		with st.status("Batch processing Prompts..."):
			progress_bar = st.progress(0)
			total_rows = len(df)
			result_rows = []
			for index, row in df.iterrows():
				#["subject", "level", "section_tags", "activity_title", "activity_notes", "additional_prompts", "duration", "number_of_components", "knowledge_base"]
				# Update the progress bar
				progress = (index + 1) / total_rows
				progress_bar.progress(min(progress, 1.0))
				subject = row['subject']
				level = row['level']
				section_tags = row['section_tags']
				activity_title = row['activity_title']
				activity_notes = row['activity_notes']
				duration = row['duration']
				knowledge_base = row['knowledge_base']
				additional_prompts = row['additional_prompts']
				number_of_components = row['number_of_components']
				st.session_state.number_of_components = number_of_components
				# Formatting the template with actual session state values
				formatted_prompt = select_prompt.format(
															Level=level,
															Subject=subject,
															Section_Tags=section_tags,
															Activity_Title=activity_title,
															Activity_Notes=activity_notes,
															Additional_Prompts=additional_prompts,
															Number_of_Components=number_of_components,
															Duration=duration,
															Knowledge_Base=knowledge_base
														)

				
				#formatted_prompt
				if model != "-":
					if model.startswith("gpt"):
						component_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_openai(model, formatted_prompt, tools)
					elif model.startswith("claude"):
						formatted_prompt = formatted_prompt + "  Return the response in JSON format. Here is an example of ideal formatting for the JSON recommendation: \n" + json_response
						component_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_claude(model, formatted_prompt)
					row['components_details'] = component_details
					row['duration'] = duration
					row['completion_tokens'] = completion_tokens
					row['prompt_tokens'] = prompt_tokens
					row['total_tokens'] = total_tokens
					# Including session state values in the row
					row['session_temp'] = st.session_state.default_temp
					row['session_presence_penalty'] = st.session_state.default_presence_penalty
					row['session_frequency_penalty'] = st.session_state.default_frequency_penalty
					row['session_top_p'] = st.session_state.default_top_p
					row['session_max_tokens'] = st.session_state.default_max_tokens
					row['generated_response'] = response_str
					result_rows.append(row)
			# Update the session state with the updated DataFrame					
			updated_df = pd.DataFrame(result_rows)
			st.session_state.prompt_df = updated_df
		st.data_editor(st.session_state.prompt_df)


def batch_call_claude(model, formatted_prompt):
	start_time = datetime.now() 
	client = anthropic.Anthropic(api_key=return_claude_key())
	message = client.messages.create(
	model=model,
	max_tokens=st.session_state.default_max_tokens,
	top_p=st.session_state.default_top_p,
	temperature=st.session_state.default_temp,
	messages=[
		{
			"role": "user", 
			"content": formatted_prompt
		},
	]
	) #.content[0].text
	#st.write(message) #break it down into parts
 
	# Initialize variables with default values at the start
	
	activity_details = extract_lesson_content_from_json_claude(message, st.session_state.number_of_components)
	end_time = datetime.now()  # Capture the end time after processing
	duration = (end_time - start_time).total_seconds()  # Calculate duration in seconds
	input_tokens = None
	output_tokens = None
	total_tokens = None

	# Extract the 'usage' attribute if it exists
	if hasattr(message, 'usage'):
		usage = message.usage
		# Check for each attribute within 'usage' and assign them if they exist
		if hasattr(usage, 'input_tokens'):
			input_tokens = usage.input_tokens
		if hasattr(usage, 'output_tokens'):
			output_tokens = usage.output_tokens
		# Calculate total_tokens only if both input_tokens and output_tokens are available
		if input_tokens is not None and output_tokens is not None:
			total_tokens = input_tokens + output_tokens
   
	response_str = str(message)
	
	return activity_details, duration, output_tokens, input_tokens, total_tokens, response_str


def extract_lesson_content_from_json_claude(message_object, expected_components_count):

	component_details = {
					'activity_description': 'No description provided',
					'activity_instruction': 'No instructions provided',
					'actual_components_count': 0,
					'expected_components_count': expected_components_count,
					'mismatch_warning': False,
					'components': [],
					'error': None
					}

	try:
		# Accessing the first content block's text to get the JSON string
		if message_object.content and isinstance(message_object.content, list):
			raw_json_string = message_object.content[0].text
		else:
			raise ValueError("Invalid message format. Cannot find the JSON content.")
		
		# Parse the JSON string
		message_data = json.loads(raw_json_string)
		
		recommendations = message_data.get('recommendations', {})
  
  
		# Extract the activity recommendation details
		activity_recommendation = recommendations.get('activityRecommendation', {})
		component_details['activity_description'] = clean_html_tags(activity_recommendation.get('activityDescription', {}).get('richtext', 'No description provided'))
		component_details['activity_instruction'] = clean_html_tags(activity_recommendation.get('activityInstruction', {}).get('richtext', 'No instructions provided'))
		
		component_recommendations = recommendations.get('componentRecommendations', [])
		actual_components_count = len(component_recommendations)
		component_details['actual_components_count'] = actual_components_count

		# Check for mismatch in the expected and actual components counts
		if actual_components_count != expected_components_count:
			component_details['mismatch_warning'] = True
			# If the count matches, you might choose to acknowledge this in your application logic

		# Iterate over each component to extract details
		for component in component_recommendations:
			component_type = "Unknown"  # Default value if the component doesn't match known types
			component_data = {}  # Initialize the data dictionary for this component
			
			if 'text' in component:
				component_type = "Text Content"
				component_data['text'] = clean_html_tags(component['text'].get('richtext', 'No text provided'))
			elif 'multipleChoiceQuestion' in component:
				mcq = component['multipleChoiceQuestion']
				component_type = "Multiple Choice Question"
				component_data.update({
					'question': clean_html_tags(mcq.get('question', {}).get('richtext', 'No question provided')),
					'duration': mcq.get('duration', 0),
					'totalMarks': mcq.get('totalMarks', 0),
					'answers': [clean_html_tags(answer.get('richtext', 'No answer provided')) for answer in mcq.get('answers', [])],
					'distractors': [clean_html_tags(distractor.get('richtext', 'No distractor provided')) for distractor in mcq.get('distractors', [])]
				})
			elif 'freeResponseQuestion' in component:
				frq = component['freeResponseQuestion']
				component_type = "Free Response Question"
				component_data.update({
					'question': clean_html_tags(frq.get('question', {}).get('richtext', 'No question provided')),
					'duration': frq.get('duration', 0),
					'totalMarks': frq.get('totalMarks', 0),
					'suggestedAnswer': [clean_html_tags(answer.get('richtext', '')) for answer in frq.get('suggestedAnswer', [])]
				})
			elif 'poll' in component:
				poll = component['poll']
				component_type = "Poll"
				component_data.update({
					'question': clean_html_tags(poll.get('question', {}).get('richtext', 'No poll question provided')),
					'options': [clean_html_tags(option.get('richtext', 'No option provided')) for option in poll.get('options', [])]
				})
			elif 'discussionQuestion' in component:
				dq = component['discussionQuestion']
				component_type = "Discussion Question"
				component_data.update({
					'topic': dq.get('topic', 'No topic provided'),
					'question': clean_html_tags(dq.get('question', {}).get('richtext', 'No discussion question provided'))
				})
			
			# Add the extracted component details to the components list in component_details
			component_details['components'].append({
				'type': component_type,
				'data': component_data
			})


	except Exception as e:
		component_details['error'] = str(e)

	return component_details


def batch_call_openai(model, edited_prompt, tools):
	start_time = datetime.now()
	st.session_state.openai_prompt = edited_prompt
	client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_openai_key()	
	)
	#openai.api_key = return_openai_key()
	#os.environ["OPENAI_API_KEY"] = return_openai_key()
	#st.title("Api Call with JSON")
	#MODEL = "gpt-3.5-turbo"
	
	response = client.chat.completions.create(
		model=model,
		messages=[
		#{"role": "system", "content": "You are a helpful assistant designed to output JSON."}, #system prompt
		{"role": "user", "content": edited_prompt},
		],
		#response_format={ "type": "json_object" }, #response format
		tools = tools,
		tool_choice = {"type": "function", "function": {"name": "get_new_component_recommendations"}},
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		top_p = st.session_state.default_top_p, #settings option
		max_tokens=st.session_state.default_max_tokens, #settings option
	)
	# st.markdown("**This is the extracted response:**")
	# st.write(response)
	activity_details = extract_lesson_content_from_json_openai(response, st.session_state.number_of_components)
	end_time = datetime.now()  # Capture the end time after processing
	duration = (end_time - start_time).total_seconds()  # Calculate duration i

	if hasattr(response.usage, 'completion_tokens'):
		completion_tokens = response.usage.completion_tokens
	if hasattr(response.usage, 'prompt_tokens'):
		prompt_tokens = response.usage.prompt_tokens
	if hasattr(response.usage, 'total_tokens'):
		total_tokens = response.usage.total_tokens
	response_str = str(response)
	
	return activity_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str


def extract_lesson_content_from_json_openai(chat_completion_object, expected_components_count):

	component_details = {
					'activity_description': 'No description provided',
					'activity_instruction': 'No instructions provided',
					'actual_components_count': 0,
					'expected_components_count': expected_components_count,
					'mismatch_warning': False,
					'components': [],
					'error': None
					}

	try:
		# Extracting the JSON string from the provided structure
		arguments_json = chat_completion_object.choices[0].message.tool_calls[0].function.arguments
		# Now, parse this JSON string to get the actual lesson content
		lesson_content = json.loads(arguments_json)
		
		recommendations = lesson_content.get('recommendations', {})
  
		# Extract the activity recommendation details
		activity_recommendation = recommendations.get('activityRecommendation', {})
		component_details['activity_description'] = clean_html_tags(activity_recommendation.get('activityDescription', {}).get('richtext', 'No description provided'))
		component_details['activity_instruction'] = clean_html_tags(activity_recommendation.get('activityInstruction', {}).get('richtext', 'No instructions provided'))
		
		component_recommendations = recommendations.get('componentRecommendations', [])
		actual_components_count = len(component_recommendations)
		component_details['actual_components_count'] = actual_components_count

		# Check for mismatch in the expected and actual components counts
		if actual_components_count != expected_components_count:
			component_details['mismatch_warning'] = True
			# If the count matches, you might choose to acknowledge this in your application logic

		# Iterate over each component to extract details
		for component in component_recommendations:
			component_type = "Unknown"  # Default value if the component doesn't match known types
			component_data = {}  # Initialize the data dictionary for this component
			
			if 'text' in component:
				component_type = "Text Content"
				component_data['text'] = clean_html_tags(component['text'].get('richtext', 'No text provided'))
			elif 'multipleChoiceQuestion' in component:
				mcq = component['multipleChoiceQuestion']
				component_type = "Multiple Choice Question"
				component_data.update({
					'question': clean_html_tags(mcq.get('question', {}).get('richtext', 'No question provided')),
					'duration': mcq.get('duration', 0),
					'totalMarks': mcq.get('totalMarks', 0),
					'answers': [clean_html_tags(answer.get('richtext', 'No answer provided')) for answer in mcq.get('answers', [])],
					'distractors': [clean_html_tags(distractor.get('richtext', 'No distractor provided')) for distractor in mcq.get('distractors', [])]
				})
			elif 'freeResponseQuestion' in component:
				frq = component['freeResponseQuestion']
				component_type = "Free Response Question"
				component_data.update({
					'question': clean_html_tags(frq.get('question', {}).get('richtext', 'No question provided')),
					'duration': frq.get('duration', 0),
					'totalMarks': frq.get('totalMarks', 0),
					'suggestedAnswer': [clean_html_tags(answer.get('richtext', '')) for answer in frq.get('suggestedAnswer', [])]
				})
			elif 'poll' in component:
				poll = component['poll']
				component_type = "Poll"
				component_data.update({
					'question': clean_html_tags(poll.get('question', {}).get('richtext', 'No poll question provided')),
					'options': [clean_html_tags(option.get('richtext', 'No option provided')) for option in poll.get('options', [])]
				})
			elif 'discussionQuestion' in component:
				dq = component['discussionQuestion']
				component_type = "Discussion Question"
				component_data.update({
					'topic': dq.get('topic', 'No topic provided'),
					'question': clean_html_tags(dq.get('question', {}).get('richtext', 'No discussion question provided'))
				})
			
			# Add the extracted component details to the components list in component_details
			component_details['components'].append({
				'type': component_type,
				'data': component_data
			})


	except Exception as e:
		component_details['error'] = str(e)

	return component_details


def upload_csv():
	# Upload CSV file using st.file_uploader
	uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
	if "api_key" not in st.session_state:
		st.session_state.api_key = return_openai_key()
	#st.session_state.prompt_history = []
	if "prompt_df" not in st.session_state:
		st.session_state.prompt_df = None

	if uploaded_file is not None:
		try:
			df = pd.read_csv(uploaded_file)

			# Check if the number of rows is greater than 300
			if len(df) > 300:
				# Truncate the DataFrame to 300 rows
				df = df.head(300)

				# Display a warning
				st.warning("The uploaded CSV file contains more than 300 rows. It has been truncated to the first 300 rows.")

			st.session_state.prompt_df = df

		except Exception as e:
			st.write("There was an error processing the CSV file.")
			st.write(e)

	# Check if the DataFrame exists before calling st.data_editor
	if st.session_state.prompt_df is not None:
		st.session_state.prompt_df.columns = st.session_state.prompt_df.columns.str.lower()
		st.session_state.prompt_df = st.data_editor(st.session_state.prompt_df, num_rows="dynamic", height=500)
		return True
	else:
		return False
	


def check_column_values(df, required_columns):
	 # Convert required columns to lowercase
	required_columns = [col.lower() for col in required_columns]
	
	missing_columns = [col for col in required_columns if col not in df.columns]
	if missing_columns:
		st.error(f"Missing columns: {', '.join(missing_columns)}")
		return False
	else:
		st.session_state.prompt_df = df.dropna(subset=[col for col in required_columns if col != 'rubrics'])
		return True