"""Generate 25 pilot text document images and metadata.csv for Phase 2 preparation."""

import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS = [
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
    print(f"Generated: {out_path.name}")


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
    print(f"Total pilot images: {len(DOCUMENTS)}")


if __name__ == "__main__":
    main()
