import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO
from PIL import Image
from PIL import Image as PILImage
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
import re

# Load Excel File from GitHub
def load_data():
    excel_url = "https://raw.githubusercontent.com/Robi-Show/Quote-Tool/main/Ariento%20Pricing%202025.xlsx"
    response = requests.get(excel_url)
    if response.status_code != 200:
        st.error("Failed to fetch the Excel file. Please check the file URL.")
        st.stop()

    excel_file = BytesIO(response.content)
    try:
        ariento_plans = pd.read_excel(excel_file, sheet_name="Ariento Plans")
        license_types = pd.read_excel(excel_file, sheet_name="Ariento License Type")
        microsoft_licenses = pd.read_excel(excel_file, sheet_name="Microsoft Seat Licenses")
    except KeyError as e:
        st.error(f"Missing sheet or column in the Excel file: {e}")
        st.stop()
    return ariento_plans, license_types, microsoft_licenses

# Load data
ariento_plans, license_types, microsoft_licenses = load_data()

# Title and Description
try:
    logo = Image.open("Ariento Logo Blue.png")
    st.image(logo, width=200)
except FileNotFoundError:
    st.error("Logo file not found. Please upload 'Ariento Logo Blue.png'.")

st.markdown('<h1 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Quote Tool</h1>', unsafe_allow_html=True)
st.markdown('<hr style="border: 1px solid #E8A33D;">', unsafe_allow_html=True)
st.markdown('<p style="font-family: Arial; font-size: 12pt; line-height: 1.15; color: #3265A7;">This tool helps you generate a quote based on Ariento Pricing 2025.</p>', unsafe_allow_html=True)

# Add Section Separator
def section_separator():
    st.markdown('<hr style="border: 1px solid #E8A33D;">', unsafe_allow_html=True)

# Add Company Name Input
company_name = st.text_input("Enter Company Name")

# Validate Company Name for File Name
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

# Step 1: Select Ariento Plan
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Licenses</h2>', unsafe_allow_html=True)
ariento_plan = st.selectbox("Select an Ariento Plan", ariento_plans["Plan Name"].unique(), key="selectbox_ariento_plan")

# Filter License Types
filtered_licenses = license_types[license_types["Plan"] == ariento_plan]

st.write("### Seat Types")
seat_types = {}

# Dynamic Seat Type Selection
seat_type_options = filtered_licenses["Seat Type"].unique()
while True:
    cols = st.columns(2)
    with cols[0]:
        seat_type = st.selectbox("Select a Seat Type", ["Select Seat Type"] + list(seat_type_options), key=f"seat_type_{len(seat_types)}")
    if seat_type == "Select Seat Type" or seat_type == "":
        break
    with cols[1]:
        quantity = st.number_input(f"Quantity for {seat_type}", min_value=0, value=1)
    if quantity > 0:
        price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
        cost = quantity * price
        st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
        seat_types[seat_type] = quantity

# Step 2: Microsoft and Other Licenses
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Microsoft & Other Licenses</h2>', unsafe_allow_html=True)
filtered_microsoft = microsoft_licenses[microsoft_licenses["Plan"] == ariento_plan]
microsoft_seats = {}

# Dynamic Microsoft License Selection
microsoft_license_options = list(filtered_microsoft["License"].unique()) + ["Other"]
row_counter = 0

while True:
    cols = st.columns(2)
    with cols[0]:
        microsoft_license = st.selectbox(
            "Select a Microsoft License or Other for more options",
            ["Select License"] + microsoft_license_options,
            key=f"microsoft_license_{row_counter}"
        )
    if microsoft_license == "Select License" or microsoft_license == "":
        break

    if microsoft_license == "Other":
        with cols[1]:
            other_license = st.selectbox(
                "Select from Available Licenses",
                ["Select License"] + list(microsoft_licenses["License"].unique()),
                key=f"other_license_{row_counter}"
            )
        if other_license != "Select License":
            microsoft_license = other_license  # Update to selected license from "Other"

    # Fetch price and allow quantity update
    with cols[1]:
        quantity = st.number_input(
            f"Quantity for {microsoft_license}",
            min_value=0,
            value=1,
            key=f"microsoft_quantity_{row_counter}"
        )
    if quantity > 0:
        price_query = microsoft_licenses.loc[microsoft_licenses["License"] == microsoft_license, "Price"]
        price = price_query.values[0] if not price_query.empty else 0.0
        cost = quantity * price
        st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
        microsoft_seats[microsoft_license] = quantity

    row_counter += 1

# Step 3: Onboarding
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Onboarding</h2>', unsafe_allow_html=True)
onboarding_type = st.selectbox(
    "Select Onboarding Payment Type", 
    ["Monthly Payments, 1-Year Subscription", "Monthly Payments, 3-Year Subscription (50% off)", 
     "Annual Payment, 1 Year Subscription (50% off)", "Other", "None"]
)

if onboarding_type == "None":
    onboarding_price = "Not Required"
elif onboarding_type == "Other":
    onboarding_price = st.number_input("Enter Onboarding Price", min_value=0.0, value=3000.0)
else:
    grouping_one_total = sum(
        quantity * (
            filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
            if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
        ) for seat_type, quantity in seat_types.items()
    )
    if "50% off" in onboarding_type:
        onboarding_price = max(grouping_one_total * 1, 3000.00)
    else:
        onboarding_price = max(grouping_one_total * 2, 3000.00)

if onboarding_price != "Not Required":
    st.write(f"Onboarding Price: ${onboarding_price:.2f}")
else:
    st.write(f"Onboarding Price: {onboarding_price}")

# Separate Costs Calculation
ariento_cost = sum(
    quantity * (
        filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
        if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
    ) for seat_type, quantity in seat_types.items()
)
microsoft_cost = sum(
    quantity * (
        microsoft_licenses.loc[microsoft_licenses["License"] == license, "Price"].values[0]
        if not microsoft_licenses.loc[microsoft_licenses["License"] == license, "Price"].empty else 0.0
    ) for license, quantity in microsoft_seats.items()
)

# Display Separate Costs
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Separate Costs</h2>', unsafe_allow_html=True)
st.write(f"### Ariento Onboarding (One-Time): {onboarding_price if onboarding_price == 'Not Required' else f'${onboarding_price:.2f}'}")
st.write(f"### Monthly Ariento Cost (Recurring): ${ariento_cost:.2f}")
st.write(f"### Monthly Microsoft/Other License Costs (Recurring): ${microsoft_cost:.2f}")

# Summary Table
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Summary of Selected Items</h2>', unsafe_allow_html=True)
data = []

# Add seat types
for seat_type, quantity in seat_types.items():
    price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0] if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Seat Type", seat_type, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add Microsoft or Other licenses to summary
for license, quantity in microsoft_seats.items():
    price = microsoft_licenses.loc[microsoft_licenses["License"] == license, "Price"].values[0] if not microsoft_licenses.loc[microsoft_licenses["License"] == license, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Microsoft License", license, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add onboarding
if onboarding_price != "Not Required":
    data.append(["Onboarding", onboarding_type, 1, f"${onboarding_price:.2f}", f"${onboarding_price:.2f}"])
else:
    data.append(["Onboarding", onboarding_type, 1, onboarding_price, onboarding_price])

# Display table
summary_df = pd.DataFrame(data, columns=["Category", "Item", "Quantity", "Price Per Unit", "Total Cost"])
st.table(summary_df.style.hide(axis='index'))

# Display current date and time
date_time_now = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
st.markdown(f'<p style="font-family: Arial; font-size: 12pt; color: #3265A7;">Date and Time: {date_time_now}</p>', unsafe_allow_html=True)

# Legal Jargon
st.markdown(
    """
    <div style="font-family: Arial; font-size: 12pt; line-height: 1.15; color: #3265A7; margin-top: 20px;">
        <strong>Legal Notice:</strong><br>
        This quote is valid for 30 days from the date of issuance. Prices are subject to change after this period 
        and are contingent upon availability and market conditions at the time of order placement. This quote does 
        not constitute a binding agreement and is provided for informational purposes only. Terms and conditions 
        may apply. Please contact us with any questions or for further clarification.
    </div>
  """,
    unsafe_allow_html=True
)

# Exportable Summary Table
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Summary of Selected Items</h2>', unsafe_allow_html=True)

# Generate CSV
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv_data = convert_df_to_csv(summary_df)

st.download_button(
    label="Download Summary as CSV",
    data=csv_data,
    file_name="summary_table.csv",
    mime="text/csv"
)

# Generate PDF Function
def generate_pdf(df, company_name):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Add Logo with Aspect Ratio Maintained
    try:
        logo_path = "Ariento Logo Blue.png"
        pil_image = PILImage.open(logo_path)
        original_width, original_height = pil_image.size
        max_width, max_height = 150, 75  # Maximum dimensions for the logo
        aspect_ratio = original_width / original_height

        if original_width > max_width:
            resized_width = max_width
            resized_height = max_width / aspect_ratio
        else:
            resized_width = original_width
            resized_height = original_height

        if resized_height > max_height:
            resized_height = max_height
            resized_width = max_height * aspect_ratio

        elements.append(ReportLabImage(logo_path, width=resized_width, height=resized_height))
        elements.append(Spacer(1, 12))  # Add space after logo
    except Exception as e:
        elements.append(Paragraph(f"Error loading logo: {str(e)}", getSampleStyleSheet()['Normal']))

    # Add Company Name
    elements.append(Paragraph(f"Company: {company_name}", getSampleStyleSheet()['Normal']))
    
    # Add Date and Time
    current_datetime = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
    elements.append(Paragraph(f"Date and Time: {current_datetime}", getSampleStyleSheet()['Normal']))

    # Add Separate Costs
    elements.append(Paragraph(f"Ariento Onboarding (One-Time): {onboarding_price if onboarding_price == 'Not Required' else f'${onboarding_price:.2f}'}", getSampleStyleSheet()['Heading2']))
    elements.append(Paragraph(f"Monthly Ariento Cost (Recurring): ${ariento_cost:.2f}", getSampleStyleSheet()['Heading2']))
    elements.append(Paragraph(f"Monthly Microsoft/Other License Costs (Recurring): ${microsoft_cost:.2f}", getSampleStyleSheet()['Heading2']))

    # Define a ParagraphStyle for word wrapping
    style = ParagraphStyle(
        name="WrappedText",
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        wordWrap="LTR",
    )
    # Format the table data with wrapped items
    table_data = [list(df.columns)]  # Header row
    for row in df.values.tolist():
        # Wrap the "Item" column text (assume it's the second column)
        row[1] = Paragraph(str(row[1]), style)  # Wrap the Item column
        table_data.append(row)

    # Create and style the table
    table = Table(table_data, colWidths=[100, 150, 50, 100, 100])  # Adjust column widths
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E8A33D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F7F7F7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    table.setStyle(style)
    elements.append(table)
    elements.append(Spacer(1, 12))  # Add space after table

    # Add Legal Notice
    legal_notice = (
        "This quote is valid for 30 days from the date of issuance. Prices are subject to change after this period "
        "and are contingent upon availability and market conditions at the time of order placement. This quote does "
        "not constitute a binding agreement and is provided for informational purposes only. Terms and conditions "
        "may apply. Please contact us with any questions or for further clarification."
    )
    elements.append(Paragraph(legal_notice, getSampleStyleSheet()['Normal']))

    pdf.build(elements)
    buffer.seek(0)
    return buffer

# Generate PDF Data
pdf_data = generate_pdf(summary_df, company_name)

# Format the PDF file name
if company_name:
    sanitized_company_name = sanitize_filename(company_name)
    pdf_file_name = f"{sanitized_company_name}_Quote_{datetime.datetime.now().strftime('%Y-%m-%d')}.pdf"
else:
    pdf_file_name = f"Quote_{datetime.datetime.now().strftime('%Y-%m-%d')}.pdf"

# Download Button for PDF
st.download_button(
    label="Download Summary as PDF",
    data=pdf_data,
    file_name=pdf_file_name,
    mime="application/pdf"
)