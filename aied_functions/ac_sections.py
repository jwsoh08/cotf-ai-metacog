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
DEFAULT_LESSON_TAGS = 'Algebra, Geometry'
DEFAULT_LESSON_TITLE = 'Introduction to Algebra'
DEFAULT_LESSON_NOTES = 'This lesson covers the basics of algebraic expressions and equations.'
DEFAULT_ADDITIONAL_PROMPTS = 'Include hands-on activities and real-life examples'
DEFAULT_NUMBER_OF_SECTIONS = 3
AC_MODEL_LIST = config_handler.get_config_values('menu_lists', 'AC_MODEL_LIST')


def sections_single_call():
	# Initialize default values if not already set
	if 'level' not in st.session_state:
		st.session_state.level = LEVELS[0]
	if 'subject' not in st.session_state:
		st.session_state.subject = SUBJECTS[0]
	# Set default values for lesson details if not already set
	if 'lesson_tags' not in st.session_state:
		st.session_state.lesson_tags = DEFAULT_LESSON_TAGS
	if 'lesson_title' not in st.session_state:
		st.session_state.lesson_title = DEFAULT_LESSON_TITLE
	if 'lesson_notes' not in st.session_state:
		st.session_state.lesson_notes = DEFAULT_LESSON_NOTES
	if 'additional_prompts' not in st.session_state:
		st.session_state.additional_prompts = DEFAULT_ADDITIONAL_PROMPTS
	if 'number_of_sections' not in st.session_state:
		st.session_state.number_of_sections = DEFAULT_NUMBER_OF_SECTIONS
	

	# UI for section generation
	c1, c2, c3 = st.columns([1, 1, 3])
	st.write("### Section generation")
	with c1:
		level = st.selectbox("Select your level:", options=LEVELS, index=0)
		st.session_state.level = level
	with c2:
		subject = st.selectbox("Select your subject:", options=SUBJECTS, index=0)
		st.session_state.subject = subject
   
	lesson_tags = st.text_input("Enter Lesson Tags (Learning Objectives):", value=st.session_state.lesson_tags)
	st.session_state.lesson_tags = lesson_tags
	lesson_title = st.text_input("Lesson Title:", value=st.session_state.lesson_title)
	st.session_state.lesson_title = lesson_title
	lesson_notes = st.text_area("Lesson Notes:", value=st.session_state.lesson_notes)
	st.session_state.lesson_notes = lesson_notes
	additional_prompts = st.text_area("Additional Prompts/Instructions:", value=st.session_state.additional_prompts)
	st.session_state.additional_prompts = additional_prompts
	number_of_sections = st.number_input("Number of Sections:", min_value=1, value=st.session_state.number_of_sections)
	st.session_state.number_of_sections = number_of_sections
 
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)
 	# Button to confirm and potentially generate the lesson sections
	if model != "-":
		if model.startswith("gpt"):
			generate_section_openai(model)
		elif model.startswith("claude"):
			generate_section_claude(model)


def generate_section_claude(model):
	if "claude_prompt" not in st.session_state:
		st.session_state.claude_prompt = ""
	# Constructing the prompt from the session state
	template = ("As an experienced {Level} {Subject} teacher, design a lesson flow comprising sections "
				"that helps students achieve the following learning outcomes: {Lesson_Tags} "
				"The title of the lesson is {Lesson_Title} and brief notes are: {Lesson_Notes} "
				"You should also consider: {Additional_Prompts} "
				"Suggest {Number_of_Sections} sections for this lesson. "
				"Your output should only be rich text, do not include hyperlinks, code snippets, "
				"mathematical formulas, or xml. Your output should be a series of sections. "
				"For each section, provide (i) a title, (ii) notes about how a teacher might enact the section "
				"and other information that might be useful for the teacher when designing this section. "
				"You should also output a lesson description that describes the lesson to the student, "
				"the lesson description should be at most five sentences long.")
 
	prompt_options = {
		"AC Claude Section Production Prompt": st.session_state.ac_claude_section_production_prompt,
		"AC Claude Section Development Prompt 1": st.session_state.ac_claude_section_development_prompt_1,
		"AC Claude Section Development Prompt 2": st.session_state.ac_claude_section_development_prompt_2,
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
		Lesson_Tags=st.session_state.get('lesson_tags', 'Lesson Tags'),
		Lesson_Title=st.session_state.get('lesson_title', 'Lesson Title'),
		Lesson_Notes=st.session_state.get('lesson_notes', 'Lesson Notes'),
		Additional_Prompts=st.session_state.get('additional_prompts', 'Additional Prompts'),
		Number_of_Sections=st.session_state.get('number_of_sections', 1)
	)

	# Here, you would call the Claude API with the formatted prompt
	# For simulation, let's format a JSON response as described and store it in session state
	example_response = {
		"recommendations": {
			"lessonDescription": {
				"richtext": "<p>Welcome to the lesson! This lesson is designed based on your inputs.</p>"
			},
			"sectionRecommendations": [
				{
					"sectionTitle": "Introduction to the Topic",
					"sectionNotes": {
						"richtext": "<p>Begin the lesson by introducing the main concepts.</p>"
					}
				},
				{
					"sectionTitle": "Deep Dive",
					"sectionNotes": {
						"richtext": "<p>Explore the subject in depth with interactive activities.</p>"
					}
				}
			]
		}
	}
	
	
	
	editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


	# Convert the example response to JSON string for demonstration
	#json_response = json.dumps(example_response, indent=4)
	
	json_response = st.session_state.ac_claude_section_example_prompt
  
	if st.checkbox("Load Claude Example JSON", key="claude_tools"):
		json_response = json.dumps(example_response, indent=4)
 
	# Display the formatted prompt in Streamlit for demonstration purposes
	appended_prompt = editable_prompt + "  Return the response in JSON format. Here is an example of ideal formatting for the JSON recommendation: \n" + json_response

	st.write(f":blue[Full claude API prompt]:")
	st.write(f"{appended_prompt}")
	# Normally, you would replace the example_response with the actual API response
	# For demonstration, we'll update the session state with the example JSON response
	if st.button("Generate Sections"):
		start_time = datetime.now() 
		with st.status("Generating sections..."):
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
			display_lesson_from_json_claude(message, st.session_state.number_of_sections)
			end_time = datetime.now()  # Capture the end time after processing
			duration = (end_time - start_time).total_seconds()  # Calculate duration in seconds
			st.write(f"Processing time: {duration} seconds")
	
	# Display the JSON formatted response in Streamlit for demonstration purposes
	


def generate_section_openai(model):
	if 'openai_prompt' not in st.session_state:
		st.session_state.openai_prompt = ""

	# Template with placeholders
	template = ("As an experienced {Level} {Subject} teacher, design a lesson flow comprising sections "
				"that helps students achieve the following learning outcomes: {Lesson_Tags} "
				"The title of the lesson is {Lesson_Title} and brief notes are: {Lesson_Notes} "
				"You should also consider: {Additional_Prompts} "
				"Suggest {Number_of_Sections} sections for this lesson. "
				"Your output should only be rich text, do not include hyperlinks, code snippets, "
				"mathematical formulas, or xml. Your output should be a series of sections. "
				"For each section, provide (i) a title, (ii) notes about how a teacher might enact the section "
				"and other information that might be useful for the teacher when designing this section. "
				"You should also output a lesson description that describes the lesson to the student, "
				"the lesson description should be at most five sentences long.")
	
	prompt_options = {
		"AC OpenAI Section Production Prompt": st.session_state.ac_openai_section_production_prompt,
		"AC OpenAI Section Development Prompt 1": st.session_state.ac_openai_section_development_prompt_1,
		"AC OpenAI Section Development Prompt 2": st.session_state.ac_openai_section_development_prompt_2,
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
		Lesson_Tags=st.session_state.get('lesson_tags', 'Lesson Tags'),
		Lesson_Title=st.session_state.get('lesson_title', 'Lesson Title'),
		Lesson_Notes=st.session_state.get('lesson_notes', 'Lesson Notes'),
		Additional_Prompts=st.session_state.get('additional_prompts', 'Additional Prompts'),
		Number_of_Sections=st.session_state.get('number_of_sections', 1)
	)
	
	st.session_state.openai_prompt = formatted_prompt
	# Display the formatted prompt in Streamlit (for demonstration purposes)
	edited_prompt = st.text_area("Generated Prompt", value=st.session_state.openai_prompt, height=300)
	
	if st.button("Generate Sections"):
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
				tool_choice = {"type": "function", "function": {"name": "get_new_section_recommendations"}},
				temperature=st.session_state.default_temp, #settings option
				presence_penalty=st.session_state.default_presence_penalty, #settings option
				frequency_penalty=st.session_state.default_frequency_penalty, #settings option
				top_p = st.session_state.default_top_p, #settings option
				max_tokens=st.session_state.default_max_tokens, #settings option
			)
			st.markdown("**This is the extracted response:**")
			st.write(response)
			display_lesson_from_json_openai(response, st.session_state.number_of_sections)
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
		"AC OpenAI Tools Section Production Prompt": st.session_state.ac_openai_tools_section_production_prompt,
		"AC OpenAI Tools Section Development Prompt 1": st.session_state.ac_openai_tools_section_development_prompt_1,
	}
	
	# Let the user select a tools format by name
	selected_format_name = st.selectbox("Select your functional tools format: (JSON)", tuple(tools_format_options.keys()))

	# Set the j_tools_format to the corresponding session state value based on the selected name
	j_tools_format = tools_format_options[selected_format_name]

	# Display the selected tools format in a text area for editing
	st.markdown(j_tools_format, unsafe_allow_html=True)
	st.divider()
	return j_tools_format


def clean_html_tags(html_content):
	"""
	Removes HTML tags from a string.
	"""
	# Regular expression to match HTML tags
	clean_text = re.sub('<.*?>', '', html_content)
	return clean_text

def display_lesson_from_json_openai(chat_completion_object, expected_sections_count):
	try:
		# Assuming chat_completion_object is the direct response object you received
		# Extract the JSON string from the response
		tool_calls = chat_completion_object.choices[0].message.tool_calls[0]
		lesson_json_string = tool_calls.function.arguments
		
		# Now, parse this JSON string to get the actual lesson content
		lesson_content = json.loads(lesson_json_string)
		
		recommendations = lesson_content.get('recommendations', {})
		
		# Extract and clean the lesson description from HTML tags
		lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
		clean_lesson_description = clean_html_tags(lesson_description)
		st.subheader("Lesson Description:")
		st.write(clean_lesson_description)
		
		section_recommendations = recommendations.get('sectionRecommendations', [])
		actual_sections_count = len(section_recommendations)
		if actual_sections_count != expected_sections_count:
			st.warning(f"Expected {expected_sections_count} sections, but found {actual_sections_count}. Please verify the lesson plan.")
		else:
			st.success(f"Number of sections matches the expected count: {expected_sections_count}.")
		
		for index, section in enumerate(section_recommendations, start=1):
			section_title = section.get('sectionTitle', 'No title')
			# Clean section notes from HTML tags
			section_notes = section.get('sectionNotes', {}).get('richtext', 'No notes provided.')
			clean_section_notes = clean_html_tags(section_notes)
			
			st.subheader(f"Section {index}: {section_title}")
			st.write(clean_section_notes)
	
	except Exception as e:
		st.error(f"Error processing the lesson content: {e}")

def display_lesson_from_json_claude(message_object, expected_sections_count):
	try:
		# Accessing the first content block's text to get the JSON string
		if message_object.content and isinstance(message_object.content, list):
			raw_json_string = message_object.content[0].text
			raw_json_string = raw_json_string.replace('<recommendation>', '').replace('</recommendation>', '')
		else:
			raise ValueError("Invalid message format. Cannot find the JSON content.")
		
		# Parse the JSON string
		message_data = json.loads(raw_json_string)
		
		# Proceed with extracting and displaying the lesson details...
		recommendations = message_data.get('recommendations', {})
		
		lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
		clean_lesson_description = clean_html_tags(lesson_description)
		st.subheader("Lesson Description:")
		st.write(clean_lesson_description)
		
		section_recommendations = recommendations.get('sectionRecommendations', [])
		actual_sections_count = len(section_recommendations)
		if actual_sections_count != expected_sections_count:
			st.error(f"Expected {expected_sections_count} sections, but found {actual_sections_count} sections.")
		else:
			st.success(f"Number of sections matches the expected count: {expected_sections_count}.")
		
		for index, section in enumerate(section_recommendations, start=1):
			section_title = section.get('sectionTitle', 'No title')
			section_notes = section.get('sectionNotes', {}).get('richtext', 'No notes provided.')
			clean_section_notes = clean_html_tags(section_notes)
			
			st.subheader(f"Section {index}: {section_title}")
			st.write(clean_section_notes)
	
	except Exception as e:
		st.error(f"Error processing the lesson content: {e}")


#---------------------------------Mass API Call---------------------------------#	

def sections_mass_call():
	#select the model
	model = st.selectbox("Select the model:", options=AC_MODEL_LIST, index=0)

	st.write("Mass API call JSON format: ")
	st.write(":red[Ensure your CSV file has the following columns: subject, level, lesson_tags, lesson_title, lesson_notes, additional_prompts, number_of_sections]")
	if upload_csv():
		if st.button("Cancel Upload"):
			st.session_state.prompt_df = None
		pass_test = check_column_values(st.session_state.prompt_df , ["subject", "level", "lesson_tags", "lesson_title", "lesson_notes", "additional_prompts", "number_of_sections"])
		if not pass_test:
			st.error("Please upload a CSV file with the required columns or modify the dataframe")
		if pass_test:
			if model != "-":
				batch_call(model)
	

def batch_call(model):
	
	if model.startswith("gpt"):
	
		# Template with placeholders
		template = ("As an experienced {Level} {Subject} teacher, design a lesson flow comprising sections "
					"that helps students achieve the following learning outcomes: {Lesson_Tags} "
					"The title of the lesson is {Lesson_Title} and brief notes are: {Lesson_Notes} "
					"You should also consider: {Additional_Prompts} "
					"Suggest {Number_of_Sections} sections for this lesson. "
					"Your output should only be rich text, do not include hyperlinks, code snippets, "
					"mathematical formulas, or xml. Your output should be a series of sections. "
					"For each section, provide (i) a title, (ii) notes about how a teacher might enact the section "
					"and other information that might be useful for the teacher when designing this section. "
					"You should also output a lesson description that describes the lesson to the student, "
					"the lesson description should be at most five sentences long.")
		
		prompt_options = {
			"AC OpenAI Section Production Prompt": st.session_state.ac_openai_section_production_prompt,
			"AC OpenAI Section Development Prompt 1": st.session_state.ac_openai_section_development_prompt_1,
			"AC OpenAI Section Development Prompt 2": st.session_state.ac_openai_section_development_prompt_2,
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
		template = ("As an experienced {Level} {Subject} teacher, design a lesson flow comprising sections "
				"that helps students achieve the following learning outcomes: {Lesson_Tags} "
				"The title of the lesson is {Lesson_Title} and brief notes are: {Lesson_Notes} "
				"You should also consider: {Additional_Prompts} "
				"Suggest {Number_of_Sections} sections for this lesson. "
				"Your output should only be rich text, do not include hyperlinks, code snippets, "
				"mathematical formulas, or xml. Your output should be a series of sections. "
				"For each section, provide (i) a title, (ii) notes about how a teacher might enact the section "
				"and other information that might be useful for the teacher when designing this section. "
				"You should also output a lesson description that describes the lesson to the student, "
				"the lesson description should be at most five sentences long.")
 
		prompt_options = {
			"AC Claude Section Production Prompt": st.session_state.ac_claude_section_production_prompt,
			"AC Claude Section Development Prompt 1": st.session_state.ac_claude_section_development_prompt_1,
			"AC Claude Section Development Prompt 2": st.session_state.ac_claude_section_development_prompt_2,
			}

		# Let the user select a prompt by name
		selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

		# Set the select_prompt to the corresponding session state value based on the selected name
		select_prompt = prompt_options[selected_prompt_name]
	
		if st.checkbox("Load Claude Sample Prompt", key="c_prompt"):
			select_prompt = template

		# Display the selected prompt
		st.write(select_prompt)
	
	
 
		# formatted_prompt = select_prompt.format(
		# 	Level=st.session_state.get('level', 'Level'),
		# 	Subject=st.session_state.get('subject', 'Subject'),
		# 	Lesson_Tags=st.session_state.get('lesson_tags', 'Lesson Tags'),
		# 	Lesson_Title=st.session_state.get('lesson_title', 'Lesson Title'),
		# 	Lesson_Notes=st.session_state.get('lesson_notes', 'Lesson Notes'),
		# 	Additional_Prompts=st.session_state.get('additional_prompts', 'Additional Prompts'),
		# 	Number_of_Sections=st.session_state.get('number_of_sections', 1)
		# )

		# Here, you would call the Claude API with the formatted prompt
		# For simulation, let's format a JSON response as described and store it in session state
		example_response = {
			"recommendations": {
				"lessonDescription": {
					"richtext": "<p>Welcome to the lesson! This lesson is designed based on your inputs.</p>"
				},
				"sectionRecommendations": [
					{
						"sectionTitle": "Introduction to the Topic",
						"sectionNotes": {
							"richtext": "<p>Begin the lesson by introducing the main concepts.</p>"
						}
					},
					{
						"sectionTitle": "Deep Dive",
						"sectionNotes": {
							"richtext": "<p>Explore the subject in depth with interactive activities.</p>"
						}
					}
				]
			}
		}
		
		
		
		#editable_prompt = st.text_area("Edit the prompt before sending:", value=formatted_prompt, height=300)


		# Convert the example response to JSON string for demonstration
		#json_response = json.dumps(example_response, indent=4)
		
		json_response = st.session_state.ac_claude_section_example_prompt
	
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
				lesson_tags = row['lesson_tags']
				lesson_title = row['lesson_title']
				lesson_notes = row['lesson_notes']
				additional_prompts = row['additional_prompts']
				number_of_sections = row['number_of_sections']
	
				# Formatting the template with actual session state values
				formatted_prompt = select_prompt.format(
															Level=level,
															Subject=subject,
															Lesson_Tags=lesson_tags,
															Lesson_Title=lesson_title,
															Lesson_Notes=lesson_notes,
															Additional_Prompts=additional_prompts,
															Number_of_Sections=number_of_sections
														)

				
				#formatted_prompt
				if model != "-":
					if model.startswith("gpt"):
						lesson_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_openai(model, formatted_prompt, tools)
					elif model.startswith("claude"):
						formatted_prompt = formatted_prompt + "  Return the response in JSON format. Here is an example of ideal formatting for the JSON recommendation: \n" + json_response
						lesson_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str = batch_call_claude(model, formatted_prompt)
					row['lesson_details'] = lesson_details
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
	
	lesson_details = extract_lesson_content_from_json_claude(message, st.session_state.number_of_sections)
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
	
	return lesson_details, duration, output_tokens, input_tokens, total_tokens, response_str


def extract_lesson_content_from_json_claude(message_object, expected_sections_count):
	lesson_details = {
		'lesson_description': 'NA',
		'sections': [],
		'expected_sections_count': expected_sections_count,
		'actual_sections_count': 0,
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
		lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
		lesson_details['lesson_description'] = clean_html_tags(lesson_description)
		
		# Extract section recommendations and their count
		section_recommendations = recommendations.get('sectionRecommendations', [])
		actual_sections_count = len(section_recommendations)
		lesson_details['actual_sections_count'] = actual_sections_count
		
		# Check for mismatch in the expected and actual section counts
		if actual_sections_count != expected_sections_count:
			lesson_details['mismatch_warning'] = True
		
		# Extract and store details for each section
		for section in section_recommendations:
			section_title = section.get('sectionTitle', 'No title')
			section_notes = section.get('sectionNotes', {}).get('richtext', 'No notes provided.')
			clean_section_notes = clean_html_tags(section_notes)
			lesson_details['sections'].append({'title': section_title, 'notes': clean_section_notes})

	except Exception as e:
		lesson_details['error'] = str(e)

	return lesson_details



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
		tool_choice = {"type": "function", "function": {"name": "get_new_section_recommendations"}},
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		top_p = st.session_state.default_top_p, #settings option
		max_tokens=st.session_state.default_max_tokens, #settings option
	)
	# st.markdown("**This is the extracted response:**")
	# st.write(response)
	lesson_details = extract_lesson_content_from_json_openai(response, st.session_state.number_of_sections)
	end_time = datetime.now()  # Capture the end time after processing
	duration = (end_time - start_time).total_seconds()  # Calculate duration i

	if hasattr(response.usage, 'completion_tokens'):
		completion_tokens = response.usage.completion_tokens
	if hasattr(response.usage, 'prompt_tokens'):
		prompt_tokens = response.usage.prompt_tokens
	if hasattr(response.usage, 'total_tokens'):
		total_tokens = response.usage.total_tokens
	response_str = str(response)
	
	return lesson_details, duration, completion_tokens, prompt_tokens, total_tokens, response_str


# def extract_lesson_content_from_json_openai(chat_completion_object, expected_sections_count):
# 	lesson_details = {
# 		'lesson_description': 'NA',
# 		'sections': [],
# 		'expected_sections_count': expected_sections_count,
# 		'actual_sections_count': 0,
# 		'mismatch_warning': False,
# 		'error': None
# 	}

# 	try:
# 		# Assuming chat_completion_object is the JSON object you received
# 		tool_calls = chat_completion_object['choices'][0]['message']['tool_calls'][0]
# 		lesson_json_string = tool_calls['function']['arguments']
		
# 		# Now, parse this JSON string to get the actual lesson content
# 		lesson_content = json.loads(lesson_json_string)
		
# 		recommendations = lesson_content.get('recommendations', {})
		
# 		# Extract and clean the lesson description from HTML tags
# 		lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
# 		lesson_details['lesson_description'] = lesson_description  # Assuming a utility function clean_html_tags is available
		
# 		section_recommendations = recommendations.get('sectionRecommendations', [])
# 		actual_sections_count = len(section_recommendations)
# 		lesson_details['actual_sections_count'] = actual_sections_count
# 		if actual_sections_count != expected_sections_count:
# 			lesson_details['mismatch_warning'] = True
		
# 		for section in section_recommendations:
# 			section_title = section.get('sectionTitle', 'No title')
# 			section_notes = section.get('sectionNotes', {}).get('richtext', 'No notes provided.')
# 			lesson_details['sections'].append({'title': section_title, 'notes': section_notes})

# 	except Exception as e:
# 		lesson_details['error'] = str(e)

# 	return lesson_details

def extract_lesson_content_from_json_openai(chat_completion_object, expected_sections_count):
    lesson_details = {
        'lesson_description': 'NA',
        'sections': [],
        'expected_sections_count': expected_sections_count,
        'actual_sections_count': 0,
        'mismatch_warning': False,
        'error': None
    }

    try:
        # Access the attributes of chat_completion_object using dot notation
        tool_calls = chat_completion_object.choices[0].message.tool_calls[0]
        lesson_json_string = tool_calls.function.arguments
        
        # Assuming the arguments is already a dictionary or needs to be parsed as JSON
        lesson_content = json.loads(lesson_json_string) if isinstance(lesson_json_string, str) else lesson_json_string
        
        recommendations = lesson_content.get('recommendations', {})
        
        # Extract and clean the lesson description from HTML tags
        lesson_description = recommendations.get('lessonDescription', {}).get('richtext', 'No lesson description provided.')
        lesson_details['lesson_description'] = lesson_description  # Assuming a utility function clean_html_tags is available
        
        section_recommendations = recommendations.get('sectionRecommendations', [])
        actual_sections_count = len(section_recommendations)
        lesson_details['actual_sections_count'] = actual_sections_count
        if actual_sections_count != expected_sections_count:
            lesson_details['mismatch_warning'] = True
        
        for section in section_recommendations:
            section_title = section.get('sectionTitle', 'No title')
            section_notes = section.get('sectionNotes', {}).get('richtext', 'No notes provided.')
            clean_section_notes = clean_html_tags(section_notes)
            lesson_details['sections'].append({'title': section_title, 'notes': clean_section_notes})

    except Exception as e:
        lesson_details['error'] = str(e)

    return lesson_details


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