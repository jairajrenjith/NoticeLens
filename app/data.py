"""Sample circulars (for 'Try a sample') and labelled seed data for the Tier-2 classifier."""

SAMPLES = [
    {
        "id": "fee",
        "label": "💰 Semester fee notice",
        "text": """COLLEGE OF ENGINEERING TRIVANDRUM
Office of the Principal
No. ACD/F2/4471/2026                                                   Date: 28/10/2026

CIRCULAR

Sub: Remittance of semester fee for S3 and S5 B.Tech students – reg.

Dear Students,

It is hereby informed that all S3 and S5 B.Tech students of all branches are required to remit the semester tuition fee of Rs. 12,500/- along with the special fee of Rs. 1,200/- through the online fee portal of the institution. The last date for payment of fee without fine is 3rd November 2026. Students remitting the fee after the said date shall be liable to pay a fine of Rs. 500/- and the final date for remittance with fine is 10 November 2026.

Students who fail to remit the fee within the stipulated date will not be permitted to register for the end semester examinations and their names will be removed from the rolls. Students availing fee concession / e-grantz are directed to submit the copy of the approval letter at the Academic Section (Room 104, Main Block) on or before 3rd November 2026.

The receipt of payment must be downloaded and kept safely for future reference. For any queries regarding the payment, contact the accounts section during office hours (10:00 AM to 4:00 PM).

This is issued with the approval of the Principal.

Regards,
Registrar
College of Engineering Trivandrum
accounts@cet.ac.in""",
    },
    {
        "id": "exam",
        "label": "📝 Series exam timetable",
        "text": """CIRCULAR No. EXAM/S5/112/2026

Sub: Second Series Test – S5 B.Tech (All Branches) – Schedule

Dear Students,

The Second Series Test for S5 B.Tech students of all branches will commence on 6th November 2026 and conclude on 12th November 2026. The examinations will be conducted in the forenoon session from 9:30 AM to 11:00 AM. The detailed subject wise time table is published on the department notice boards and the college website.

Students must report to the examination hall at least 15 minutes before the commencement of the exam. Students are required to carry their college ID card and hall ticket to the examination hall; students without ID cards will not be allowed to write the examination. Mobile phones and smart watches are strictly prohibited inside the examination hall.

Students with attendance shortage below 75% are directed to meet their respective faculty advisors before 4th November 2026. The marks of the series test will be considered for the internal assessment. No retest will be conducted for students who are absent without valid medical certificate.

Controller of Examinations""",
    },
    {
        "id": "placement",
        "label": "💼 Placement drive",
        "text": """CAREER GUIDANCE AND PLACEMENT UNIT (CGPU)

Campus Recruitment Drive – Infosys – 2027 Batch

Dear Students,

Greetings from CGPU!

We are pleased to inform you that Infosys Ltd. will be conducting a campus recruitment drive for the 2027 passing out batch (S7 students) of CSE, ECE, EEE and AE branches. Eligibility criteria: minimum 6.5 CGPA with no active backlogs at the time of the drive. The offered role is Systems Engineer with a CTC of Rs. 3,60,000 per annum.

Interested and eligible students must register through the placement portal at https://placement.cet.ac.in on or before 5 November 2026, 5:00 PM. The pre-placement talk will be held on 8th November 2026 at 10:00 AM in the CGPU Hall, followed by the online aptitude test. Students should bring an updated resume, two passport size photographs and a copy of all mark lists.

Students who register and fail to attend the drive will be debarred from the next two placement drives. Formal dress code is mandatory.

Regards,
Training and Placement Officer
CGPU, CET
placement@cet.ac.in
Mobile: 9495521917""",
    },
    {
        "id": "event",
        "label": "🎉 Tech fest event",
        "text": """IEEE SB CET in association with the Department of Computer Science

Dear All,

We are happy to announce "HackCET 2026", a 24-hour national level hackathon to be conducted on 21st and 22nd November 2026 at the Main Auditorium. The hackathon is open to all students of all branches and semesters. Teams can have 2 to 4 members. Exciting prizes worth Rs. 1,00,000 await the winners, along with internship opportunities from our sponsors.

Registration is free for IEEE members and Rs. 200 per team for non-members. Kindly register using the form at https://hackcet.in/register before 15th November 2026. Food and accommodation will be provided for all participants. Participants should bring their own laptops and chargers.

For queries, contact the student coordinator at 9876543210.

Thank you,
IEEE SB CET""",
    },
]

# Seed training data: (text, label). Small but enough for a TF-IDF + LogReg demo classifier.
TRAIN = [
    ("remit the semester tuition fee through the online portal before the last date", "fee"),
    ("fine of rs 500 will be levied for late payment of fees", "fee"),
    ("students availing fee concession e-grantz submit approval letter", "fee"),
    ("hostel mess fee and caution deposit must be paid", "fee"),
    ("exam registration fee to be remitted along with the application", "fee"),
    ("payment receipt to be downloaded from the accounts portal", "fee"),
    ("scholarship amount will be credited to the bank account of eligible students", "scholarship"),
    ("apply for the merit cum means scholarship on the national scholarship portal", "scholarship"),
    ("students eligible for the minority scholarship should submit income certificate", "scholarship"),
    ("renewal of e-grantz scholarship applications last date", "scholarship"),
    ("series test time table published students must carry hall ticket", "exam"),
    ("end semester examination registration revaluation results", "exam"),
    ("mobile phones prohibited inside the examination hall", "exam"),
    ("internal assessment marks retest for absent students medical certificate", "exam"),
    ("university exam schedule supplementary examination", "exam"),
    ("attendance shortage students not eligible to write the exam", "exam"),
    ("campus recruitment drive eligibility cgpa no active backlogs ctc", "placement"),
    ("pre placement talk followed by aptitude test register on placement portal", "placement"),
    ("internship opportunity company hiring freshers resume interview", "placement"),
    ("training and placement cell mock interview resume workshop", "placement"),
    ("students debarred from next placement drive formal dress code", "placement"),
    ("hackathon technical fest workshop register teams prizes", "event"),
    ("cultural fest arts day sports meet participation", "event"),
    ("guest lecture seminar webinar by industry expert in auditorium", "event"),
    ("ieee iedc club event registration open for all students", "event"),
    ("nss ncc camp volunteers blood donation drive", "event"),
    ("college will remain closed on account of holiday", "holiday"),
    ("declared holiday due to heavy rain classes suspended", "holiday"),
    ("onam christmas vacation classes resume on", "holiday"),
    ("public holiday election working day compensatory", "holiday"),
    ("hostel admission room allotment warden mess timings", "hostel"),
    ("hostel inmates must return before gate closing time", "hostel"),
    ("mess bill hostel vacate rooms during vacation", "hostel"),
    ("class timetable revised faculty advisor meeting attendance", "academic"),
    ("course registration elective selection curriculum", "academic"),
    ("submission of project report lab record assignment", "academic"),
    ("parent teacher meeting progress report", "academic"),
    ("library books return due id card renewal", "academic"),
]
