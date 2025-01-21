from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
from scripts import  FileConverter, FileCleaner, HeaderExtractor, ResumeCleaner, NameComparator, EmailExtractor, PhoneNumberExtractor, DataMerger, ExperienceExtractor, RandomExperienceExtractor, ResumeExperienceExtractor, ExperienceProcessor, PDFMatcher  # Importing all required classes

# Initialize the Flask application
app = Flask(__name__)

# Define the folder where files will be uploaded
UPLOAD_FOLDER = 'Data_pass'  # Folder for saving the uploaded files
PROCESSED_FOLDER = 'Prased_resumes'  # Folder where processed CSV files will be saved
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size 16MB

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to render the index.html page
@app.route('/')
def index():
    return render_template('index.html')


# Route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    files = request.files.getlist('file')  # Get multiple files from the form
    if not files:
        return "No files selected", 400
    
    # Save uploaded files to the Data_pass folder
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # After saving the files, we start processing each step sequentially
    
    # Step 1: File Conversion
    input_folder = UPLOAD_FOLDER
    output_folder = "processed_pdfs/"
    file_converter = FileConverter(input_folder, output_folder)
    file_converter.process_folder()

    # Step 2: File Cleaning
    csv_file = "scripts/Filename_unwanted.csv"  # Adjust as needed, could be input from previous steps
    folder_path = "processed_pdfs/"
    output_folder = "Prased_resumes/test_trainname_demo.csv"
    file_cleaner = FileCleaner(folder_path, csv_file, output_folder)
    file_cleaner.process_files()
    file_cleaner.save_results()

    # Step 3: Header Extraction
    folder_path = "processed_pdfs/"
    header_extractor = HeaderExtractor(folder_path)
    df = header_extractor.process_folder_and_store_in_dataframe()
    output_path = "scripts/parsed_headername.csv"  # Adjust path if neededFileProcessor
    header_extractor.save_results_to_csv(output_path)

    # Step 4: Resume Cleaning
    unwanted_words_csv = "scripts/Header_unwanted_new.csv"  # Adjust as needed
    resume_cleaner = ResumeCleaner(unwanted_words_csv, "parsed_headername.csv", "Prased_resumes/cleaned_parsed_headername.csv")
    resume_cleaner.clean_resumes()
    resume_cleaner.save_cleaned_resumes()

    # Step 5: Name Comparison
    filename_csv = "Prased_resumes/test_trainname_demo.csv"  # Adjust as needed
    headername_csv = "Prased_resumes/cleaned_parsed_headername.csv"  # Adjust as needed
    name_comparator = NameComparator(filename_csv, headername_csv, "Prased_resumes/Demo_overall_name.csv")
    name_comparator.clean_extracted_line()
    final_df = name_comparator.compare_names()
    name_comparator.save_comparison_results(final_df)

    # Step 6: Email Extraction
    input_folder = "processed_pdfs/"
    email_extractor = EmailExtractor(input_folder, "Prased_resumes/email.csv")
    emails_df = email_extractor.extract_first_email_from_folder()
    email_extractor.save_emails_to_csv(emails_df)

    # Step 7: Phone Number Extraction
    input_folder = "processed_pdfs/"
    phone_number_extractor = PhoneNumberExtractor(input_folder, "Prased_resumes/phone_numbers.csv")
    phone_numbers_df = phone_number_extractor.extract_phone_numbers_from_folder()
    phone_numbers_df['processed_phone_number'] = phone_numbers_df.apply(phone_number_extractor.process_phone_numbers, axis=1)
    phone_number_extractor.save_phone_numbers_to_csv(phone_numbers_df)

    # Step 8: Data Merging
    # Instantiate the DataMerger class
    phone_numbers_csv = os.path.join('Prased_resumes', 'phone_numbers.csv')
    email_csv = os.path.join('Prased_resumes', 'email.csv')
    name_csv = os.path.join('Prased_resumes', 'Demo_overall_name.csv')
    output_csv_path = os.path.join('Prased_resumes', 'overall_Details.csv')

    data_merger = DataMerger(phone_numbers_csv, email_csv, name_csv, output_csv_path)

    # Process and save the merged data
    data_merger.process_data()

     # Step 9: Extracting Experience Data
    folder_path = 'processed_pdfs/'
    output_csv_path = 'Prased_resumes/Fileexp_data.csv'
    
    # Instantiate the ExperienceExtractor class and extract experience data
    experience_extractor = ExperienceExtractor(folder_path, output_csv_path)
    experience_extractor.extract_and_save()
    
    # Step 10: Extracting RandomExperience Data
    folder_path = 'processed_pdfs/'
    output_csv_path = 'Prased_resumes/Randomexp_data.csv'
    
    # Instantiate the ExperienceExtractor class and extract experience data
    random_experience_extractor = RandomExperienceExtractor(folder_path, output_csv_path)
    random_experience_extractor.extract_and_process_experience()

    # Step 11: Extracting ResumeExperience Data
    folder_path = 'processed_pdfs/'  # Path to your folder containing PDFs
    search_words_file = 'scripts/CSV_serachExpheader.csv'  # CSV file containing search words
    output_csv_path = 'Prased_resumes/csv_output_experience.csv'  # Path to save the results
    # Create an instance of the class
    resume_extractor = ResumeExperienceExtractor(folder_path, search_words_file, output_csv_path)
    # Run the process
    resume_extractor.run()

    # Step 12: Extracting compareExperience Data
    processor = ExperienceProcessor(
        filename_csv='Prased_resumes/Fileexp_data.csv',
        search_csv='Prased_resumes/Randomexp_data.csv',
        content_csv='Prased_resumes/csv_output_experience.csv',
        output_csv='Prased_resumes/Compare_exp.csv'
    )
    
    # Generate the final DataFrame and save it
    processor.generate_final_dataframe()

    # Step 13: Extracting skillMatch Data
    pdf_folder_path = 'processed_pdfs/'
    jd_csv_path = 'scripts/All_JD.csv'
    output_csv_path = 'Prased_resumes/Skill_match_results.csv'
    pdf_matcher = PDFMatcher(pdf_folder_path, jd_csv_path, output_csv_path)
    results_df = pdf_matcher.process_pdfs_and_find_matches()
    

    # Return to index with a success message
    return redirect(url_for('index', message="Files uploaded and processed successfully"))


# Route to display CSV file content
@app.route('/view_csv/<filename>')
def view_csv(filename):
    try:
        # Path to the processed CSV files
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        with open(file_path, 'r') as file:
            data = file.read().splitlines()

        return render_template('view_csv.html', data=data, filename=filename)
    except Exception as e:
        return str(e)


# Route to download CSV file
@app.route('/download_csv/<filename>')
def download_csv(filename):
    try:
        # Path to the processed CSV files
        file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return str(e)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8867, threaded=True, debug=False)
