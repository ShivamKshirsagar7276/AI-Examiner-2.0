from io import BytesIO
from datetime import datetime


def generate_photocopy_pdf(submission, exam):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit

    buffer        = BytesIO()
    c             = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    def draw_watermark():
        c.saveState()
        c.setFont("Helvetica-Bold", 60)
        c.setFillColorRGB(0.88, 0.88, 0.88)
        c.setFillAlpha(0.25)
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "PHOTOCOPY")
        c.restoreState()

    def draw_header(page_num):
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(0.35, 0.24, 0.21)
        c.drawString(50, height - 50, "GRADY — AI Examiner")

        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, height - 70,  f"Exam: {exam.title}  |  Subject: {exam.subject}")
        c.drawString(50, height - 85,  f"Roll No: {submission.roll_number}  |  Class: {exam.class_name}  |  Division: {exam.division}")
        c.drawString(50, height - 100, f"Total Marks: {submission.total_marks} / {submission.max_marks}  |  Grade: {submission.grade}  |  {submission.percentage}%")
        c.drawString(50, height - 115, f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}  |  Page {page_num}")

        c.setStrokeColorRGB(0.35, 0.24, 0.21)
        c.setLineWidth(1.5)
        c.line(50, height - 125, width - 50, height - 125)

    def draw_footer():
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(
            width / 2, 30,
            "OFFICIAL PHOTOCOPY — GRADY AI Examiner  |  System Generated Document"
        )

    page_num  = 1
    eval_data = submission.evaluation_json or {}
    mapped    = submission.mapped_answers or {}

    draw_watermark()
    draw_header(page_num)
    draw_footer()

    y = height - 150

    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.35, 0.24, 0.21)
    c.drawString(50, y, "Answer Sheet — Official Photocopy")
    y -= 30

    for qid, data in eval_data.items():
        if data.get("ignored_due_to_best_of"):
            continue

        if y < 120:
            c.showPage()
            page_num += 1
            draw_watermark()
            draw_header(page_num)
            draw_footer()
            y = height - 150

        final_marks = data.get("final_marks", 0)
        max_marks   = data.get("max_marks", 0)
        pct         = round((final_marks / max_marks * 100), 1) if max_marks > 0 else 0
        mark_color  = (0.09, 0.64, 0.26) if pct >= 60 else (0.85, 0.44, 0.0) if pct >= 40 else (0.86, 0.08, 0.08)

        c.setFillColorRGB(0.96, 0.94, 0.92)
        c.roundRect(45, y - 8, width - 90, 26, 6, fill=1, stroke=0)

        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.35, 0.24, 0.21)
        c.drawString(52, y + 6, f"Question {qid}")

        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(*mark_color)
        c.drawRightString(width - 52, y + 6, f"Marks: {final_marks} / {max_marks}")

        y -= 28

        student_text = mapped.get(qid, {}).get("answer_text", "")

        if student_text and str(student_text).strip():
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.1, 0.1, 0.1)
            lines = simpleSplit(str(student_text), "Helvetica", 10, width - 104)

            for line in lines:
                if y < 60:
                    c.showPage()
                    page_num += 1
                    draw_watermark()
                    draw_header(page_num)
                    draw_footer()
                    y = height - 150

                c.drawString(52, y, line)
                y -= 15
        else:
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.drawString(52, y, "No answer detected for this question.")
            y -= 15

        c.setStrokeColorRGB(0.88, 0.82, 0.78)
        c.setLineWidth(0.5)
        c.line(50, y - 5, width - 50, y - 5)
        y -= 20

    c.save()
    buffer.seek(0)
    return buffer
