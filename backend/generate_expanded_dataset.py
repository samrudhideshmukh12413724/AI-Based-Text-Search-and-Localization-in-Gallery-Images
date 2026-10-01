"""Generate expanded 56 document images and metadata.csv for Phase 2."""

import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = ROOT / "backend" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS = [
    # Pilot 1-25
    {
        "image_id": "001",
        "filename": "scholarship.jpg",
        "category": "scholarship",
        "title": "Government Scholarship",
        "subtitle": "Application 2026",
        "body": "Financial aid and merit support for undergraduate students.",
        "keywords": "scholarship government financial aid education grant",
    },
    {
        "image_id": "002",
        "filename": "scholarship_merit.jpg",
        "category": "scholarship",
        "title": "Merit Student Scholarship",
        "subtitle": "National Welfare Scheme",
        "body": "Financial assistance awarded for academic excellence in college.",
        "keywords": "merit scholarship money assistance student welfare",
    },
    {
        "image_id": "003",
        "filename": "scholarship_fellowship.jpg",
        "category": "scholarship",
        "title": "Research Fellowship Grant",
        "subtitle": "Higher Education Support",
        "body": "Monthly stipend and funding for postgraduate research scholars.",
        "keywords": "fellowship grant research funding stipend higher education",
    },
    {
        "image_id": "004",
        "filename": "loan_education.jpg",
        "category": "finance",
        "title": "Student Education Loan",
        "subtitle": "Financial Assistance Scheme",
        "body": "Low interest bank loan for college tuition and living expenses.",
        "keywords": "loan education money bank interest financial support tuition",
    },
    {
        "image_id": "005",
        "filename": "admission.jpg",
        "category": "admission",
        "title": "College Admission Form",
        "subtitle": "Academic Year 2026",
        "body": "Official application form for new student enrollment.",
        "keywords": "admission college enrollment application joining",
    },
    {
        "image_id": "006",
        "filename": "admission_engineering.jpg",
        "category": "admission",
        "title": "B.Tech Engineering Admission",
        "subtitle": "Eligibility and Guidelines",
        "body": "Entrance exam cutoff criteria and seat matrix for engineering.",
        "keywords": "engineering btech admission entrance cutoff criteria",
    },
    {
        "image_id": "007",
        "filename": "admission_counseling.jpg",
        "category": "admission",
        "title": "Centralized Counseling Notice",
        "subtitle": "Seat Allocation Round 1",
        "body": "Document verification and campus seat allotment schedule.",
        "keywords": "counseling seat allocation verification allotment campus",
    },
    {
        "image_id": "008",
        "filename": "fees.jpg",
        "category": "finance",
        "title": "College Fee Receipt",
        "subtitle": "Tuition Breakdown 2026",
        "body": "Payment voucher for semester tuition, lab, and development charges.",
        "keywords": "fees tuition receipt payment charges voucher finance",
    },
    {
        "image_id": "009",
        "filename": "fees_hostel.jpg",
        "category": "finance",
        "title": "Hostel Fee Schedule",
        "subtitle": "Maintenance and Mess Charges",
        "body": "Due dates and payment details for residential hall accommodation.",
        "keywords": "hostel fees mess charges maintenance payment due date",
    },
    {
        "image_id": "010",
        "filename": "fees_exam.jpg",
        "category": "finance",
        "title": "Examination Fee Notice",
        "subtitle": "Semester Assessment Fees",
        "body": "Late fee penalties and online payment portal instructions.",
        "keywords": "exam fees assessment payment late penalty portal",
    },
    {
        "image_id": "011",
        "filename": "exam.jpg",
        "category": "examination",
        "title": "Semester Examination Notice",
        "subtitle": "Instructions for Candidates",
        "body": "Mandatory exam hall protocols and prohibited electronic items.",
        "keywords": "exam semester notice rules candidate hall instructions",
    },
    {
        "image_id": "012",
        "filename": "exam_hall_ticket.jpg",
        "category": "examination",
        "title": "Examination Hall Ticket",
        "subtitle": "Student Admit Card 2026",
        "body": "Download admit card for university final semester theory exams.",
        "keywords": "hall ticket admit card exam download center entry",
    },
    {
        "image_id": "013",
        "filename": "exam_results.jpg",
        "category": "examination",
        "title": "Annual Examination Results",
        "subtitle": "Scorecard & Grade Report",
        "body": "Semester grade point average SGPA and marks announcement.",
        "keywords": "results scorecard marks grades sgpa score report",
    },
    {
        "image_id": "014",
        "filename": "timetable.jpg",
        "category": "academics",
        "title": "Weekly Class Timetable",
        "subtitle": "Computer Science Semester IV",
        "body": "Lecture schedule for Data Structures, AI, and Operating Systems.",
        "keywords": "timetable class schedule lecture computer science routine",
    },
    {
        "image_id": "015",
        "filename": "timetable_exam.jpg",
        "category": "academics",
        "title": "Final Examination Date Sheet",
        "subtitle": "Winter Session 2026",
        "body": "Subject wise exam schedule, timings, and classroom allocations.",
        "keywords": "datesheet exam timetable schedule winter dates timing",
    },
    {
        "image_id": "016",
        "filename": "library.jpg",
        "category": "library",
        "title": "Central Library Membership",
        "subtitle": "Student Registration Form",
        "body": "Borrowing limits, digital catalog access, and reading room timings.",
        "keywords": "library books membership catalog borrowing reading reading room",
    },
    {
        "image_id": "017",
        "filename": "library_books.jpg",
        "category": "library",
        "title": "Library Book Return Notice",
        "subtitle": "Due Dates & Overdue Fines",
        "body": "Return issued textbooks before the end of semester to avoid penalty.",
        "keywords": "library return textbooks fine overdue books penalty issue",
    },
    {
        "image_id": "018",
        "filename": "hostel.jpg",
        "category": "hostel",
        "title": "Hostel Room Allocation",
        "subtitle": "Campus Residence Form",
        "body": "Application for dormitory room and mess facility for outstation students.",
        "keywords": "hostel room accommodation dormitory mess residence living",
    },
    {
        "image_id": "019",
        "filename": "hostel_rules.jpg",
        "category": "hostel",
        "title": "Hostel Rules & Regulations",
        "subtitle": "Student Resident Guidelines",
        "body": "Curfew timings, visitor restrictions, and campus security policies.",
        "keywords": "hostel rules curfew security visitors discipline residence",
    },
    {
        "image_id": "020",
        "filename": "notice.jpg",
        "category": "notice",
        "title": "Annual Sports Day Notice",
        "subtitle": "College Athletic Meet 2026",
        "body": "Student registration for football, cricket, and track events.",
        "keywords": "notice sports athletic cricket football events tournament",
    },
    {
        "image_id": "021",
        "filename": "notice_placement.jpg",
        "category": "career",
        "title": "Campus Placement Drive",
        "subtitle": "Tech Companies Recruitment",
        "body": "Job interviews and coding tests for final year software engineers.",
        "keywords": "placement job recruitment tech company career interview hiring",
    },
    {
        "image_id": "022",
        "filename": "notice_internship.jpg",
        "category": "career",
        "title": "Summer Internship Notice",
        "subtitle": "Industry Training Programme",
        "body": "Paid internship opportunities with certificates for college students.",
        "keywords": "internship summer training industry stipend practical work",
    },
    {
        "image_id": "023",
        "filename": "application.jpg",
        "category": "administrative",
        "title": "Student ID Card Application",
        "subtitle": "Duplicate Card Reissue Form",
        "body": "Request form for lost or damaged campus identity cards.",
        "keywords": "id card identity application reissue duplicate student",
    },
    {
        "image_id": "024",
        "filename": "registration.jpg",
        "category": "administrative",
        "title": "Course Registration Portal",
        "subtitle": "Semester Enrollment Guide",
        "body": "Step by step procedure to select elective and core subjects online.",
        "keywords": "registration course electives enrollment subjects portal online",
    },
    {
        "image_id": "025",
        "filename": "bonafide_certificate.jpg",
        "category": "administrative",
        "title": "Bonafide Certificate Form",
        "subtitle": "Official Student Proof",
        "body": "Document verifying active enrollment for passport, visa, or bus pass.",
        "keywords": "bonafide certificate proof student verification passport visa",
    },
    
    # Expanded Documents 26-56
    {
        "image_id": "026",
        "filename": "scholarship_girl_child.jpg",
        "category": "scholarship",
        "title": "Pragati Scholarship for Girls",
        "subtitle": "Technical Education Support",
        "body": "Financial assistance and tuition fee reimbursement for female engineering students.",
        "keywords": "scholarship girls female women technical education aid reimbursement",
    },
    {
        "image_id": "027",
        "filename": "scholarship_merit_cum_means.jpg",
        "category": "scholarship",
        "title": "Merit Cum Means Scholarship",
        "subtitle": "Economically Weaker Section",
        "body": "College fee waiver and educational grant for students with low family income.",
        "keywords": "scholarship fee waiver grant low income poor students help",
    },
    {
        "image_id": "028",
        "filename": "admission_mba.jpg",
        "category": "admission",
        "title": "MBA Management Admission",
        "subtitle": "Group Discussion & PI Schedule",
        "body": "Admission criteria and interview rounds for master of business administration.",
        "keywords": "mba management admission business interview discussion master",
    },
    {
        "image_id": "029",
        "filename": "admission_mca.jpg",
        "category": "admission",
        "title": "MCA Admission Notice",
        "subtitle": "Computer Applications Eligibility",
        "body": "Postgraduate admissions for software development and computer application programs.",
        "keywords": "mca admission computer software applications postgraduate eligibility",
    },
    {
        "image_id": "030",
        "filename": "admission_cancellation.jpg",
        "category": "admission",
        "title": "Admission Cancellation & Refund",
        "subtitle": "Fee Refund Policy 2026",
        "body": "Procedure to withdraw admission and claim tuition fee refund before session start.",
        "keywords": "admission cancellation refund withdraw money policy drop seat",
    },
    {
        "image_id": "031",
        "filename": "fees_bus_transport.jpg",
        "category": "finance",
        "title": "Campus Bus Transport Fees",
        "subtitle": "Route & Pass Registration",
        "body": "Semester transport fee payment and bus route pass collection details.",
        "keywords": "bus transport fees pass travel commute campus route",
    },
    {
        "image_id": "032",
        "filename": "fees_late_penalty.jpg",
        "category": "finance",
        "title": "Late Fee Payment Notice",
        "subtitle": "Accounts Department",
        "body": "Penalty charges applicable after due date for pending semester tuition fees.",
        "keywords": "late fee penalty charges fine due date pending tuition accounts",
    },
    {
        "image_id": "033",
        "filename": "fees_challan.jpg",
        "category": "finance",
        "title": "Bank Fee Payment Challan",
        "subtitle": "Offline Deposit Voucher",
        "body": "Cash deposit instructions at campus bank branch for academic fees.",
        "keywords": "bank challan cash deposit voucher offline payment receipt",
    },
    {
        "image_id": "034",
        "filename": "exam_revaluation.jpg",
        "category": "examination",
        "title": "Answer Sheet Re-evaluation",
        "subtitle": "Rechecking & Photocopy Notice",
        "body": "Application form and fee per subject for grade rechecking and marks recount.",
        "keywords": "revaluation rechecking photocopy answer sheet marks grade recount",
    },
    {
        "image_id": "035",
        "filename": "exam_supplementary.jpg",
        "category": "examination",
        "title": "Supplementary Backlog Exam",
        "subtitle": "Special Remedial Examination",
        "body": "Registration form and exam dates for students clearing previous semester backlogs.",
        "keywords": "supplementary backlog remedial repeat failed exam registration",
    },
    {
        "image_id": "036",
        "filename": "exam_practical_viva.jpg",
        "category": "examination",
        "title": "Practical Lab Exam Schedule",
        "subtitle": "External Viva Voce Timetable",
        "body": "Schedule for physics, chemistry, coding labs, and project presentations.",
        "keywords": "practical lab exam viva voce external project presentation",
    },
    {
        "image_id": "037",
        "filename": "library_digital_access.jpg",
        "category": "library",
        "title": "IEEE Digital Library Access",
        "subtitle": "E-Journal & Research Database",
        "body": "Login credentials and remote proxy access for international research papers.",
        "keywords": "ieee digital library ejournal papers research articles online access",
    },
    {
        "image_id": "038",
        "filename": "library_thesis_submission.jpg",
        "category": "library",
        "title": "Thesis Hard Bound Submission",
        "subtitle": "Library Repository Archive",
        "body": "Guidelines for submitting final bound research dissertations and plagiarism reports.",
        "keywords": "thesis dissertation project submission hard bound plagiarism archive",
    },
    {
        "image_id": "039",
        "filename": "library_lost_book.jpg",
        "category": "library",
        "title": "Lost Library Book Policy",
        "subtitle": "Replacement & Recovery Fine",
        "body": "Procedure to replace missing catalog books or pay double procurement cost.",
        "keywords": "lost book missing replace library fine damage textbook",
    },
    {
        "image_id": "040",
        "filename": "hostel_mess_menu.jpg",
        "category": "hostel",
        "title": "Hostel Mess Food Menu",
        "subtitle": "Weekly Dining Schedule",
        "body": "Nutritious vegetarian and non-vegetarian food schedule in dining halls.",
        "keywords": "mess menu food dining breakfast lunch dinner meal vegetarian",
    },
    {
        "image_id": "041",
        "filename": "hostel_night_out_pass.jpg",
        "category": "hostel",
        "title": "Hostel Night Out Pass",
        "subtitle": "Parent Permission & Gate Pass",
        "body": "Leave application protocol for students visiting home on weekends.",
        "keywords": "night out pass leave home permission gate warden weekend",
    },
    {
        "image_id": "042",
        "filename": "hostel_warden_contact.jpg",
        "category": "hostel",
        "title": "Hostel Warden Directory",
        "subtitle": "Emergency Campus Contacts",
        "body": "Phone numbers and office hours of chief wardens and medical staff.",
        "keywords": "warden contact phone emergency numbers directory hostel office",
    },
    {
        "image_id": "043",
        "filename": "placement_mock_interview.jpg",
        "category": "career",
        "title": "Mock Technical Interview",
        "subtitle": "Career Development Cell",
        "body": "One on one guidance and coding interview prep with alumni mentors.",
        "keywords": "mock interview coding prep career resume practice guidance",
    },
    {
        "image_id": "044",
        "filename": "placement_shortlist.jpg",
        "category": "career",
        "title": "Campus Placement Shortlist",
        "subtitle": "Software Engineer Selects",
        "body": "List of selected students offered software developer roles and package details.",
        "keywords": "placement shortlist selected software engineer package offers hiring",
    },
    {
        "image_id": "045",
        "filename": "placement_internship_stipend.jpg",
        "category": "career",
        "title": "Google Summer Internship",
        "subtitle": "Pre-Placement Offer Track",
        "body": "Software engineering stipend and project tracks for third year students.",
        "keywords": "google internship summer stipend software engineering pre placement",
    },
    {
        "image_id": "046",
        "filename": "sports_cricket_tournament.jpg",
        "category": "sports",
        "title": "Inter-College Cricket Cup",
        "subtitle": "Annual Sports League 2026",
        "body": "Cricket team selection trials, match fixtures, and stadium ground rules.",
        "keywords": "cricket tournament sports match team trials pitch league",
    },
    {
        "image_id": "047",
        "filename": "sports_badminton_trials.jpg",
        "category": "sports",
        "title": "Badminton Championship Trials",
        "subtitle": "Singles and Doubles Squad",
        "body": "Selection trials for university sports squad at the indoor badminton court.",
        "keywords": "badminton tournament trials court racket sports indoor championship",
    },
    {
        "image_id": "048",
        "filename": "sports_gym_rules.jpg",
        "category": "sports",
        "title": "Campus Gymnasium Timings",
        "subtitle": "Fitness Center Guidelines",
        "body": "Workout slots for boys and girls with certified physical trainer supervision.",
        "keywords": "gym gymnasium workout fitness trainer timings health weights",
    },
    {
        "image_id": "049",
        "filename": "workshop_ai_bootcamp.jpg",
        "category": "workshop",
        "title": "AI & Machine Learning Workshop",
        "subtitle": "3-Day Hands-on Bootcamp",
        "body": "Deep learning, PyTorch, and NLP models practical training session.",
        "keywords": "ai artificial intelligence machine learning workshop bootcamp pytorch deep learning",
    },
    {
        "image_id": "050",
        "filename": "workshop_cloud_computing.jpg",
        "category": "workshop",
        "title": "AWS Cloud Computing Seminar",
        "subtitle": "DevOps & Cloud Architecture",
        "body": "Certified training on serverless architecture and cloud container deployment.",
        "keywords": "aws cloud computing seminar devops docker serverless architecture",
    },
    {
        "image_id": "051",
        "filename": "workshop_robotics.jpg",
        "category": "workshop",
        "title": "Robotics & IoT Hackathon",
        "subtitle": "Hardware Design Challenge",
        "body": "Build autonomous robots and IoT sensor networks with team prizes.",
        "keywords": "robotics iot hackathon hardware sensors embedded arduino prize",
    },
    {
        "image_id": "052",
        "filename": "cultural_fest_euphoria.jpg",
        "category": "cultural",
        "title": "Euphoria Annual Cultural Fest",
        "subtitle": "College Celebrations 2026",
        "body": "Dance competitions, musical concerts, fashion shows, and celebrity night.",
        "keywords": "cultural fest euphoria dance music concert celebrations festival",
    },
    {
        "image_id": "053",
        "filename": "cultural_music_auditions.jpg",
        "category": "cultural",
        "title": "College Music Band Auditions",
        "subtitle": "Vocalists & Instrumentalists",
        "body": "Rock band auditions for guitarists, drummers, and classical vocalists.",
        "keywords": "music band auditions vocalists singer guitar drums instruments",
    },
    {
        "image_id": "054",
        "filename": "cultural_drama_play.jpg",
        "category": "cultural",
        "title": "Inter-Department Drama Play",
        "subtitle": "Stage Theater Competition",
        "body": "Stage acting competition and script submissions for university theater club.",
        "keywords": "drama play theater acting script stage cultural competition",
    },
    {
        "image_id": "055",
        "filename": "notice_holiday_calendar.jpg",
        "category": "notice",
        "title": "University Holiday Calendar",
        "subtitle": "Academic Year 2026",
        "body": "List of official public holidays, festive breaks, and semester vacation dates.",
        "keywords": "holiday calendar vacation breaks festival days off schedule",
    },
    {
        "image_id": "056",
        "filename": "notice_cleanliness_drive.jpg",
        "category": "notice",
        "title": "Campus Cleanliness Drive",
        "subtitle": "NSS Student Volunteer Club",
        "body": "Tree plantation and campus green environment awareness campaign.",
        "keywords": "cleanliness nss volunteers tree plantation green campus awareness environment",
    },
]


def create_image(doc: dict) -> None:
    width, height = 750, 480
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Decorative header border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(40, 80, 140), width=3)
    draw.rectangle([(25, 25), (width - 25, 80)], fill=(240, 245, 255))

    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_body = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()

    draw.text((45, 38), doc["title"], fill=(20, 50, 110), font=font_title)
    draw.text((45, 110), doc["subtitle"], fill=(40, 40, 40), font=font_sub)
    draw.text((45, 180), doc["body"], fill=(70, 70, 70), font=font_body)
    draw.text((45, 380), f"ID: {doc['image_id']}  |  Category: {doc['category'].upper()}", fill=(120, 120, 120), font=font_body)

    out_path = DATASET_DIR / doc["filename"]
    image.save(out_path, quality=95)
    # Also save in backend/uploads for live serving
    upload_out = UPLOADS_DIR / doc["filename"]
    image.save(upload_out, quality=95)


def main():
    metadata_path = DATASET_DIR / "metadata.csv"
    with open(metadata_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "filename", "category", "expected_title", "expected_text", "keywords"])

        for doc in DOCUMENTS:
            create_image(doc)
            expected_full = f"{doc['title']} {doc['subtitle']} {doc['body']}"
            writer.writerow([
                doc["image_id"],
                doc["filename"],
                doc["category"],
                doc["title"],
                expected_full,
                doc["keywords"],
            ])

    print(f"\nMetadata written to {metadata_path}")
    print(f"Total dataset images generated: {len(DOCUMENTS)}")


if __name__ == "__main__":
    main()
