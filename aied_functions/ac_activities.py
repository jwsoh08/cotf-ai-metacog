import openai
from openai import OpenAI
import streamlit as st
from datetime import datetime
from basecode2.authenticate import return_openai_key, return_claude_key
import os
import streamlit_antd_components as sac
import configparser
import ast
import pandas as pd
import json
import anthropic
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
DEFAULT_SECTION_TITLE = 'Introduction to Algebra'
DEFAULT_SECTION_NOTES = """Begin the lesson by introducing the concept of algebra and its importance in mathematics. 
Explain the basic components of algebraic expressions, such as variables, constants, and operations. 
Use simple examples to demonstrate how to write and manipulate algebraic expressions. 
Encourage students to participate in the discussion by asking them to provide their own examples."""
DEFAULT_ADDITIONAL_PROMPTS = 'Include hands-on activities and real-life examples'
DEFAULT_NUMBER_OF_ACTIVITIES = 3
DURATION = "1 hours 30 minutes 30 seconds"
KNOWLEDGE_BASE = """
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
	st.session_state.section_duration = duration_formatted

	# Optionally, display the formatted string
	st.write("Duration:", duration_formatted)


def activities_single_call():
	# Initialize default values if not already set
	if 'level' not in st.session_state:
		st.session_state.level = LEVELS[0]
	if 'subject' not in st.session_state:
		st.session_state.subject = SUBJECTS[0]
	# Set default values for SECTION details if not already set
	if 'section_tags' not in st.session_state:
		st.session_state.section_tags = DEFAULT_SECTION_TAGS
	if 'section_title' not in st.session_state:
		st.session_state.section_title = DEFAULT_SECTION_TITLE
	if 'section_notes' not in st.session_state:
		st.session_state.section_notes = DEFAULT_SECTION_NOTES
	if 'section_duration' not in st.session_state:
		st.session_state.section_duration = DURATION
	if 'activity_additional_prompts' not in st.session_state:
		st.session_state.activity_additional_prompts = DEFAULT_ADDITIONAL_PROMPTS
	if 'number_of_activities' not in st.session_state:
		st.session_state.number_of_activities = DEFAULT_NUMBER_OF_ACTIVITIES
	if 'knowledge_base' not in st.session_state:
		st.session_state.knowledge_base = KNOWLEDGE_BASE
	

	# UI for section generation
	c1, c2, c3 = st.columns([1, 1, 3])
	st.write("### Activities generation")
	with c1:
		level = st.selectbox("Select your level:", options=LEVELS, index=0)
		st.session_state.level = level
	with c2:
		subject = st.selectbox("Select your subject:", options=SUBJECTS, index=0)
		st.session_state.subject = subject
   
	section_tags = st.text_input("Enter Section Tags (Learning Objectives):", value=st.session_state.section_tags)
	st.session_state.section_tags = section_tags
	section_title = st.text_input("Section Title:", value=st.session_state.section_title)
	st.session_state.section_title = section_title
	section_notes = st.text_area("Section Notes:", value=st.session_state.section_notes, height=300)
	st.session_state.section_notes = section_notes
	additional_prompts = st.text_area("Additional Prompts/Instructions:", value=st.session_state.activity_additional_prompts, height=300)
	st.session_state.activity_additional_prompts = additional_prompts
	knowledge_base = st.text_area("Knowledge Base:", value=st.session_state.knowledge_base, height=300)
	st.session_state.knowledge_base = knowledge_base
	get_and_display_duration()
	number_of_activities = st.number_input("Number of Activities:", min_value=1, value=st.session_state.number_of_activities)
	st.session_state.number_of_activities = number_of_activities
 
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)
 	# Button to confirm and potentially generate the section sections
	if model != "-":
		if model.startswith("gpt"):
			generate_activity_openai(model)
		elif model.startswith("claude"):
			generate_activity_claude(model)
   
def generate_activity_claude(model):
	if "claude_prompt" not in st.session_state:
		st.session_state.claude_prompt = ""
	# Constructing the prompt from the session state
	template = ("As an experienced {Level} {Subject} teacher, design a segment of a lesson that helps students achieve the following learning outcomes:  {Section_Tags}  The title of the section is {Section_Title} and brief notes are {Section_Notes}."
			 "You should also consider: {Additional_Prompts}.  Students are expected to spend {Duration} on this segment. Suggest a mix of {Number_of_Activities} activities or quizzes for this segment. The activities and quizzes should help students understand the information in {Knowledge_Base}."
			 "A quiz is a series of questions that students need to attempt, while an activity comprises of text, questions and other tasks for a student to complete.  Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml." 
			 "Your first output is a section description that describes the section to the student, the section description should be at most five sentences long.  Your next outputs should be a series of activities or quizzes. For each output,"
			 "identity whether it is an activity or quiz and then provide (i) a title, (ii) other useful notes about the activity or quiz and details about how a teacher might enact it, (iii) suggested time needed for a student to complete the activity or quiz.")
 
	prompt_options = {
			"AC Claude Activity Production Prompt": st.session_state.ac_claude_activity_production_prompt,
			"AC Claude Activity Development Prompt 1": st.session_state.ac_claude_activity_development_prompt_1,
			"AC Claude Activity Development Prompt 2": st.session_state.ac_claude_activity_development_prompt_2,
		}

	# Let the user select a prompt by name
	selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

	# Set the select_prompt to the corresponding session state value based on the selected name
	select_prompt = prompt_options[selected_prompt_name]
 
	if st.checkbox("Load Claude Sample Prompt", key="c_prompt"):
		select_prompt = template

	# Display the selected prompt
	st.write(select_prompt)
	
	
 
	formatted_prompt = select_prompt.format(
		Level=st.session_state.get('level', 'Level'),
		Subject=st.session_state.get('subject', 'Subject'),
		Section_Tags=st.session_state.get('section_tags', 'Section_Tags'),
		Section_Title=st.session_state.get('section_title', 'Section_Title'),
		Section_Notes=st.session_state.get('section_notes', 'Section_Notes'),
		Additional_Prompts=st.session_state.get('activity_additional_prompts', 'Additional_Prompts'),
		Duration=st.session_state.get('section_duration', 'Duration'),
		Number_of_Activities=st.session_state.get('number_of_activities', 'Number_of_Activities'),
		Knowledge_Base=st.session_state.get('knowledge_base', 'Knowledge_Base')
	)

	# Here, you would call the Claude API with the formatted prompt
	# For simulation, let's format a JSON response as described and store it in session state
	example_response = {
							"recommendations": {
								"sectionDescription": {
									"richtext": "<p>Introduction: In this section, we will explore the concept of tectonic plates and their global distribution. </p>"
								},
								"activityRecommendations": [
									{
										"activityType": "activity",
										"activityTitle": "Plate Tectonics Map Exploration",
										"activityNotes": {
											"richtext": "<p>Objective: Explore the global distribution of tectonic plates and identify different plate boundaries.</p>"
										},
										"activityDuration": 900
									},
									{
										"activityType": "quiz",
										"activityTitle": "Plate Boundaries Quiz",
										"activityNotes": {
											"richtext": "<p>Objective: Test your knowledge on different types of plate boundaries.</p>"
										},
										"activityDuration": 300
									}
								]
							}
						}

	
	
	
	editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


	# Convert the example response to JSON string for demonstration
	#json_response = json.dumps(example_response, indent=4)
	
	json_response = st.session_state.ac_claude_activity_example_prompt
  
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
			display_lesson_from_json_claude(message, st.session_state.number_of_activities)
			end_time = datetime.now()  # Capture the end time after processing
			duration = (end_time - start_time).total_seconds()  # Calculate duration in seconds
			st.write(f"Processing time: {duration} seconds")
	
	# Display the JSON formatted response in Streamlit for demonstration purposes

def clean_html_tags(html_text):
    # A simple function to remove HTML tags from the text
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text()

def display_lesson_from_json_claude(message_object, expected_sections_count):
    try:
        # Assuming message_object.content is a list with at least one ContentBlock
        if message_object.content and isinstance(message_object.content, list):
            raw_json_string = message_object.content[0].text

            # Remove the '<recommendation>' prefix and any possible suffix
            raw_json_string = raw_json_string.replace('<recommendation>', '').replace('</recommendation>', '')

        else:
            raise ValueError("Invalid message format. Cannot find the JSON content.")
        
        # Debugging: print the modified JSON string to inspect
        #st.write("Modified JSON String:", raw_json_string)

        # Parse the JSON string
        message_data = json.loads(raw_json_string)

        recommendations = message_data.get('recommendations', {})
        
        # Extract and display the section description
        section_description = recommendations.get('sectionDescription', {}).get('richtext', 'No section description provided.')
        clean_section_description = clean_html_tags(section_description)
        st.subheader("Section Description:")
        st.write(clean_section_description)
        
        # Extract and display activity recommendations
        activity_recommendations = recommendations.get('activityRecommendations', [])
        if len(activity_recommendations) != expected_sections_count:
            st.error(f"Expected {expected_sections_count} activities, but found {len(activity_recommendations)} activities.")
        else:
            st.success(f"Number of activities matches the expected count: {expected_sections_count}.")
        
        for index, activity in enumerate(activity_recommendations, start=1):
            activity_type = activity.get('activityType', 'No activity type')
            activity_title = activity.get('activityTitle', 'No title')
            activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
            clean_activity_notes = clean_html_tags(activity_notes)
            activity_duration = activity.get('activityDuration', 0)
            
            st.subheader(f"Activity {index}: {activity_title} ({activity_type})")
            st.write(clean_activity_notes)
            st.write(f"Duration: {activity_duration // 60} minutes")
    
    except Exception as e:
        st.error(f"Error processing the lesson content: {e}")


# def clean_html_tags(html_content):
# 	"""
# 	Removes HTML tags from a string.
# 	"""
# 	clean_text = re.sub('<.*?>', '', html_content)
# 	return clean_text

# def display_lesson_from_json_claude(message_object, expected_sections_count):
# 	try:
# 		# Assuming message_object.content is a list with at least one ContentBlock
# 		if message_object.content and isinstance(message_object.content, list):
# 			raw_json_string = message_object.content[0].text
# 		else:
# 			raise ValueError("Invalid message format. Cannot find the JSON content.")
		
# 		# Parse the JSON string
# 		message_data = json.loads(raw_json_string)
		
# 		recommendations = message_data.get('recommendations', {})
		
# 		# Extract and display the section description
# 		section_description = recommendations.get('sectionDescription', {}).get('richtext', 'No section description provided.')
# 		clean_section_description = clean_html_tags(section_description)
# 		st.subheader("Section Description:")
# 		st.write(clean_section_description)
		
# 		# Extract and display activity recommendations
# 		activity_recommendations = recommendations.get('activityRecommendations', [])
# 		if len(activity_recommendations) != expected_sections_count:
# 			st.error(f"Expected {expected_sections_count} activities, but found {len(activity_recommendations)} activities.")
# 		else:
# 			st.success(f"Number of activities matches the expected count: {expected_sections_count}.")
		
# 		for index, activity in enumerate(activity_recommendations, start=1):
# 			activity_type = activity.get('activityType', 'No activity type')
# 			activity_title = activity.get('activityTitle', 'No title')
# 			activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
# 			clean_activity_notes = clean_html_tags(activity_notes)
# 			activity_duration = activity.get('activityDuration', 0)
			
# 			st.subheader(f"Activity {index}: {activity_title} ({activity_type})")
# 			st.write(clean_activity_notes)
# 			st.write(f"Duration: {activity_duration // 60} minutes")
	
# 	except Exception as e:
# 		st.error(f"Error processing the lesson content: {e}")





#openai ============================================================================
def generate_activity_openai(model):
	if 'openai_prompt' not in st.session_state:
		st.session_state.openai_prompt = ""

	# Template with placeholders
	template = ("As an experienced {Level} {Subject} teacher, design a segment of a lesson that helps students achieve the following learning outcomes:  {Section_Tags}  The title of the section is {Section_Title} and brief notes are {Section_Notes}."
			 "You should also consider: {Additional_Prompts}.  Students are expected to spend {Duration} on this segment. Suggest a mix of {Number_of_Activities} activities or quizzes for this segment. The activities and quizzes should help students understand the information in {Knowledge_Base}."
			 "A quiz is a series of questions that students need to attempt, while an activity comprises of text, questions and other tasks for a student to complete.  Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml." 
			 "Your first output is a section description that describes the section to the student, the section description should be at most five sentences long.  Your next outputs should be a series of activities or quizzes. For each output,"
			 "identity whether it is an activity or quiz and then provide (i) a title, (ii) other useful notes about the activity or quiz and details about how a teacher might enact it, (iii) suggested time needed for a student to complete the activity or quiz.")
	
	prompt_options = {
		"AC OpenAI Activity Production Prompt": st.session_state.ac_openai_activity_production_prompt,
		"AC OpenAI Activity Development Prompt 1": st.session_state.ac_openai_activity_development_prompt_1,
		"AC OpenAI Activity Development Prompt 2": st.session_state.ac_openai_activity_development_prompt_2,
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
	formatted_prompt = select_prompt.format(
		Level=st.session_state.get('level', 'Level'),
		Subject=st.session_state.get('subject', 'Subject'),
		Section_Tags=st.session_state.get('section_tags', 'Section_Tags'),
		Section_Title=st.session_state.get('section_title', 'Section_Title'),
		Section_Notes=st.session_state.get('section_notes', 'Section_Notes'),
		Additional_Prompts=st.session_state.get('activity_additional_prompts', 'Additional_Prompts'),
		Duration=st.session_state.get('section_duration', 'Duration'),
		Number_of_Activities=st.session_state.get('number_of_activities', 'Number_of_Activities'),
		Knowledge_Base=st.session_state.get('knowledge_base', 'Knowledge_Base')
	)
 
	st.session_state.openai_prompt = formatted_prompt
	# Display the formatted prompt in Streamlit (for demonstration purposes)
	edited_prompt = st.text_area("Generated Prompt", value=st.session_state.openai_prompt, height=300)
	
	if st.button("Generate Actitivities"):
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
				tool_choice = {"type": "function", "function": {"name": "get_new_activity_recommendations"}},
				temperature=st.session_state.default_temp, #settings option
				presence_penalty=st.session_state.default_presence_penalty, #settings option
				frequency_penalty=st.session_state.default_frequency_penalty, #settings option
				top_p = st.session_state.default_top_p, #settings option
				max_tokens=st.session_state.default_max_tokens, #settings option
			)
			st.markdown("**This is the extracted response:**")
			st.write(response)
			display_lesson_from_json_openai(response, st.session_state.number_of_activities)
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
		"AC OpenAI Tools Activity Production Prompt": st.session_state.ac_openai_tools_activity_production_prompt,
		"AC OpenAI Tools Activity Development Prompt 1": st.session_state.ac_openai_tools_activity_development_prompt_1,
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
		
		# Since `recommendations` is correctly a dictionary, we directly access its elements
		if 'sectionDescription' in lesson_content['recommendations']:
			section_description = lesson_content['recommendations']['sectionDescription'].get('richtext', 'No section description provided.')
			clean_section_description = clean_html_tags(section_description)
			st.subheader("Section Description:")
			st.write(clean_section_description)
		
		if 'activityRecommendations' in lesson_content['recommendations']:
			activity_recommendations = lesson_content['recommendations']['activityRecommendations']
			actual_activities_count = len(activity_recommendations)
			if actual_activities_count != expected_sections_count:
				st.warning(f"Expected {expected_sections_count} activities, but found {actual_activities_count}. Please verify the lesson plan.")
			else:
				st.success(f"Number of activities matches the expected count: {expected_sections_count}.")

			for index, activity in enumerate(activity_recommendations, start=1):
				activity_type = activity.get('activityType', 'No activity type specified')
				activity_title = activity.get('activityTitle', 'No title')
				activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
				clean_activity_notes = clean_html_tags(activity_notes)
				activity_duration_seconds = activity.get('activityDuration', {}).get('seconds', 0)
				activity_duration = f"{activity_duration_seconds // 60} minutes"
				
				st.subheader(f"Activity {index}: {activity_title} ({activity_type})")
				st.write(clean_activity_notes)
				st.write(f"Duration: {activity_duration}")
	
	except Exception as e:
		st.error(f"Error processing the lesson content: {str(e)}")


# def display_lesson_from_json_openai(chat_completion_object, expected_sections_count):
# 	st.write("Extracting the JSON response from the API call...")
# 	try:
# 		# Extracting the JSON string from the provided structure
# 		json_string = chat_completion_object.content[0].text  # Assuming it is always the first content block and of type 'text'

		
# 		# Now, parse this JSON string to get the actual lesson content
# 		lesson_content = json.loads(json_string)

# 		# Access the 'recommendations' key after parsing the JSON
# 		recommendations = lesson_content['recommendations']

# 		# Process section description
# 		section_description = recommendations['sectionDescription'].get('richtext', 'No section description provided.')
# 		clean_section_description = clean_html_tags(section_description)
# 		st.subheader("Section Description:")
# 		st.write(clean_section_description)

# 		# Process activities
# 		activity_recommendations = recommendations['activityRecommendations']
# 		actual_activities_count = len(activity_recommendations)
# 		if actual_activities_count != expected_sections_count:
# 			st.warning(f"Expected {expected_sections_count} activities, but found {actual_activities_count}. Please verify the lesson plan.")
# 		else:
# 			st.success(f"Number of activities matches the expected count: {expected_sections_count}.")

# 		for index, activity in enumerate(activity_recommendations, start=1):
# 			activity_type = activity.get('activityType', 'No activity type specified')
# 			activity_title = activity.get('activityTitle', 'No title')
# 			activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
# 			clean_activity_notes = clean_html_tags(activity_notes)
# 			activity_duration_seconds = activity.get('activityDuration', 0)
# 			activity_duration = f"{activity_duration_seconds // 60} minutes"

# 			st.subheader(f"Activity {index}: {activity_title} ({activity_type})")
# 			st.write(clean_activity_notes)
# 			st.write(f"Duration: {activity_duration}")

# 	except Exception as e:
# 		st.error(f"Error processing the lesson content: {str(e)}")

# Assuming 'chat_completion_object' is loaded correctly and 'expected_sections_count' is defined
# You would call the function like this:
# display_lesson_from_json_openai(chat_completion_object, expected_sections_count)


#---------------------------------Mass API Call---------------------------------#	

def activities_mass_call():
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)

	st.write("Mass API call JSON format: ")
	st.write(":red[Ensure your CSV file has the following columns: subject, level, section_tags, section_title, section_notes, additional_prompts, duration, number_of_activities, knowledge_base]")
	if upload_csv():
		if st.button("Cancel Upload"):
			st.session_state.prompt_df = None
		pass_test = check_column_values(st.session_state.prompt_df , ["subject", "level", "section_tags", "section_title", "section_notes", "additional_prompts", "duration", "number_of_activities", "knowledge_base"])
		if not pass_test:
			st.error("Please upload a CSV file with the required columns or modify the dataframe")
		if pass_test:
			if model != "-":
				batch_call(model)
	

def batch_call(model):
	
	template = ("As an experienced {Level} {Subject} teacher, design a segment of a lesson that helps students achieve the following learning outcomes:  {Section_Tags}  The title of the section is {Section_Title} and brief notes are {Section_Notes}."
				"You should also consider: {Additional_Prompts}.  Students are expected to spend {Duration} on this segment. Suggest a mix of {Number_of_Activities} activities or quizzes for this segment. The activities and quizzes should help students understand the information in {Knowledge_Base}."
				"A quiz is a series of questions that students need to attempt, while an activity comprises of text, questions and other tasks for a student to complete.  Your output should only be rich text, do not include hyperlinks, code snippets, mathematical formulas or xml." 
				"Your first output is a section description that describes the section to the student, the section description should be at most five sentences long.  Your next outputs should be a series of activities or quizzes. For each output,"
				"identity whether it is an activity or quiz and then provide (i) a title, (ii) other useful notes about the activity or quiz and details about how a teacher might enact it, (iii) suggested time needed for a student to complete the activity or quiz.")

	# Check if the model is selected	
	
	
	if model.startswith("gpt"):
	
		# Template with placeholders
		prompt_options = {
		"AC OpenAI Activity Production Prompt": st.session_state.ac_openai_activity_production_prompt,
		"AC OpenAI Activity Development Prompt 1": st.session_state.ac_openai_activity_development_prompt_1,
		"AC OpenAI Activity Development Prompt 2": st.session_state.ac_openai_activity_development_prompt_2,
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
			"AC Claude Activity Production Prompt": st.session_state.ac_claude_activity_production_prompt,
			"AC Claude Activity Development Prompt 1": st.session_state.ac_claude_activity_development_prompt_1,
			"AC Claude Activity Development Prompt 2": st.session_state.ac_claude_activity_development_prompt_2,
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
								"sectionDescription": {
									"richtext": "<p>Introduction: In this section, we will explore the concept of tectonic plates and their global distribution. </p>"
								},
								"activityRecommendations": [
									{
										"activityType": "activity",
										"activityTitle": "Plate Tectonics Map Exploration",
										"activityNotes": {
											"richtext": "<p>Objective: Explore the global distribution of tectonic plates and identify different plate boundaries.</p>"
										},
										"activityDuration": 900
									},
									{
										"activityType": "quiz",
										"activityTitle": "Plate Boundaries Quiz",
										"activityNotes": {
											"richtext": "<p>Objective: Test your knowledge on different types of plate boundaries.</p>"
										},
										"activityDuration": 300
									}
								]
							}
						}
		
		
		
		#editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


		# Convert the example response to JSON string for demonstration
		#json_response = json.dumps(example_response, indent=4)
		
		json_response = st.session_state.ac_claude_activity_example_prompt
	
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
				#["subject", "level", "lesson_tags", "lesson_title", "lesson_notes", "additional_prompts", "number_of_sections"
				# Update the progress bar
				progress = (index + 1) / total_rows
				progress_bar.progress(min(progress, 1.0))
				subject = row['subject']
				level = row['level']
				section_tags = row['section_tags']
				section_title = row['section_title']
				section_notes = row['section_notes']
				duration = row['duration']
				knowledge_base = row['knowledge_base']
				additional_prompts = row['additional_prompts']
				number_of_activities = row['number_of_activities']
				st.session_state.number_of_activities = number_of_activities
	
				# Formatting the template with actual session state values
				formatted_prompt = select_prompt.format(
															Level=level,
															Subject=subject,
															Section_Tags=section_tags,
															Section_Title=section_title,
															Section_Notes=section_notes,
															Additional_Prompts=additional_prompts,
															Number_of_Activities=number_of_activities,
															Duration=duration,
															Knowledge_Base=knowledge_base
														)

				
				#formatted_prompt
				if model != "-":
					if model.startswith("gpt"):
						section_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_openai(model, formatted_prompt, tools)
					elif model.startswith("claude"):
						formatted_prompt = formatted_prompt + "  Return the response in JSON format. Here is an example of ideal formatting for the JSON recommendation: \n" + json_response
						section_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_claude(model, formatted_prompt)
					row['section_details'] = section_details
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
	
	section_details = extract_lesson_content_from_json_claude(message, st.session_state.number_of_activities)
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
	
	return section_details, duration, output_tokens, input_tokens, total_tokens, response_str


def extract_lesson_content_from_json_claude(message_object, expected_activities_count):
	section_details = {
		'section_description': 'NA',
		'activities': [],
		'expected_activities_count': expected_activities_count,
		'actual_activities_count': 0,
		'mismatch_warning': False,
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
		
		# Extract the recommendations from the parsed JSON
		recommendations = message_data.get('recommendations', {})
		
		# Extract and clean the lesson description from HTML tags
		#lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
		section_description = recommendations.get('sectionDescription', {}).get('richtext', 'No section description provided.')
		section_details['lesson_description'] = clean_html_tags(section_description)
		
		# Extract and display activity recommendations
		activity_recommendations = recommendations.get('activityRecommendations', [])
		section_details['actual_activities_count'] = len(activity_recommendations) 
		
		# Check for mismatch in the expected and actual section counts
		if len(activity_recommendations) != expected_activities_count:
			section_details['mismatch_warning'] = True
		
		for index, activity in enumerate(activity_recommendations, start=1):
			activity_type = activity.get('activityType', 'No activity type')
			activity_title = activity.get('activityTitle', 'No title')
			activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
			clean_activity_notes = clean_html_tags(activity_notes)
			activity_duration = activity.get('activityDuration', 0)

			# Calculate the duration in minutes
			activity_duration_minutes = activity_duration // 60

			# Store the activity details in a dictionary
			activity_details = {
				'type': activity_type,
				'title': activity_title,
				'notes': clean_activity_notes,
				'duration': activity_duration_minutes
			}

			# Append the activity details to the activities list in section_details
			section_details['activities'].append(activity_details)

	except Exception as e:
		section_details['error'] = str(e)

	return section_details


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
		tool_choice = {"type": "function", "function": {"name": "get_new_activity_recommendations"}},
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		top_p = st.session_state.default_top_p, #settings option
		max_tokens=st.session_state.default_max_tokens, #settings option
	)
	# st.markdown("**This is the extracted response:**")
	# st.write(response)
	section_details = extract_lesson_content_from_json_openai(response, st.session_state.number_of_activities)
	end_time = datetime.now()  # Capture the end time after processing
	duration = (end_time - start_time).total_seconds()  # Calculate duration i

	if hasattr(response.usage, 'completion_tokens'):
		completion_tokens = response.usage.completion_tokens
	if hasattr(response.usage, 'prompt_tokens'):
		prompt_tokens = response.usage.prompt_tokens
	if hasattr(response.usage, 'total_tokens'):
		total_tokens = response.usage.total_tokens
	response_str = str(response)
	
	return section_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str


def extract_lesson_content_from_json_openai(chat_completion_object, expected_activities_count):
	section_details = {
		'section_description': 'NA',
		'activities': [],
		'expected_activities_count': expected_activities_count,
		'actual_activities_count': 0,
		'mismatch_warning': False,
		'error': None
	}

	try:
		# Access the attributes of chat_completion_object using dot notation
		arguments_json = chat_completion_object.choices[0].message.tool_calls[0].function.arguments
		
		# Now, parse this JSON string to get the actual lesson content
		message_data = json.loads(arguments_json)
		
		# Extract the recommendations from the parsed JSON
		recommendations = message_data.get('recommendations', {})
		
		# Extract and clean the lesson description from HTML tags
		#lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
		section_description = recommendations.get('sectionDescription', {}).get('richtext', 'No section description provided.')
		section_details['lesson_description'] = clean_html_tags(section_description)
		
		# Extract and display activity recommendations
		activity_recommendations = recommendations.get('activityRecommendations', [])
		section_details['actual_activities_count'] = len(activity_recommendations) 
		
		# Check for mismatch in the expected and actual section counts
		if len(activity_recommendations) != expected_activities_count:
			section_details['mismatch_warning'] = True
		
		for index, activity in enumerate(activity_recommendations, start=1):
			activity_type = activity.get('activityType', 'No activity type')
			activity_title = activity.get('activityTitle', 'No title')
			activity_notes = activity.get('activityNotes', {}).get('richtext', 'No notes provided.')
			clean_activity_notes = clean_html_tags(activity_notes)
			activity_duration = activity.get('activityDuration', 0)

			# Calculate the duration in minutes
			activity_duration_minutes = activity_duration // 60

			# Store the activity details in a dictionary
			activity_details = {
				'type': activity_type,
				'title': activity_title,
				'notes': clean_activity_notes,
				'duration': activity_duration_minutes
			}

			# Append the activity details to the activities list in section_details
			section_details['activities'].append(activity_details)

	except Exception as e:
		section_details['error'] = str(e)

	return section_details


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