import streamlit as st
import pandas as pd
import datetime
import requests
from io import BytesIO
from PIL import Image
from PIL import Image as PILImage
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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

st.markdown(
    '<h1 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Quote Tool</h1>',
    unsafe_allow_html=True
)
st.markdown('<hr style="border: 1px solid #E8A33D;">', unsafe_allow_html=True)
st.markdown(
    '<p style="font-family: Arial; font-size: 12pt; line-height: 1.15; color: #3265A7;">'
    'This tool helps you generate a quote based on Ariento Pricing 2025.</p>',
    unsafe_allow_html=True
)

# Section Separator function
def section_separator():
    st.markdown('<hr style="border: 1px solid #E8A33D;">', unsafe_allow_html=True)

# Company Name Input and filename sanitization
company_name = st.text_input("Enter Company Name")
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

# Step 1: Select Ariento Plan
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Licenses</h2>',
    unsafe_allow_html=True
)
ariento_plan = st.selectbox(
    "Select an Ariento Plan",
    ariento_plans["Plan Name"].unique(),
    key="selectbox_ariento_plan"
)

# Filter License Types
filtered_licenses = license_types[license_types["Plan"] == ariento_plan]

st.write("### Seat Types")
seat_types = {}

# Dynamic Seat Type Selection using a while loop
seat_type_options = filtered_licenses["Seat Type"].unique()
while True:
    cols = st.columns(2)
    with cols[0]:
        seat_type = st.selectbox(
            "Select a Seat Type",
            ["Select Seat Type"] + list(seat_type_options),
            key=f"seat_type_{len(seat_types)}"
        )
    if seat_type == "Select Seat Type" or seat_type == "":
        break
    with cols[1]:
        quantity = st.number_input(f"Quantity for {seat_type}", min_value=0, value=1, key=f"seat_qty_{len(seat_types)}")
    if quantity > 0:
        price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
        cost = quantity * price
        st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
        seat_types[seat_type] = quantity

# Step 2: Microsoft and Other Licenses
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Microsoft & Other Licenses</h2>',
    unsafe_allow_html=True
)
filtered_microsoft = microsoft_licenses[microsoft_licenses["Plan"] == ariento_plan]
microsoft_seats = {}

microsoft_license_options = list(filtered_microsoft["License"].unique()) + ["Other"]
row_counter = 0

while True:
    cols = st.columns(2)
    with cols[0]:
        ms_license = st.selectbox(
            "Select a Microsoft License or Other for more options",
            ["Select License"] + microsoft_license_options,
            key=f"microsoft_license_{row_counter}"
        )
    if ms_license == "Select License" or ms_license == "":
        break

    if ms_license == "Other":
        with cols[1]:
            other_license = st.selectbox(
                "Select from Available Licenses",
                ["Select License"] + list(microsoft_licenses["License"].unique()),
                key=f"other_license_{row_counter}"
            )
        if other_license != "Select License":
            ms_license = other_license  # Update to selected license from "Other"

    with cols[1]:
        quantity = st.number_input(
            f"Quantity for {ms_license}",
            min_value=0,
            value=1,
            key=f"microsoft_qty_{row_counter}"
        )
    if quantity > 0:
        price_query = microsoft_licenses.loc[microsoft_licenses["License"] == ms_license, "Price"]
        price = price_query.values[0] if not price_query.empty else 0.0
        cost = quantity * price
        st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
        microsoft_seats[ms_license] = quantity

    row_counter += 1

# Step 3: Onboarding and Discount
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Onboarding</h2>',
    unsafe_allow_html=True
)

if ariento_plan == "Enclave One":
    onboarding_price = "Not Required"
    onboarding_type = "Not Required"
    st.write(f"Onboarding Price: {onboarding_price}")
else:
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
                filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].values[0]
                if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].empty else 0.0
            ) for seat, quantity in seat_types.items()
        )
        if "50% off" in onboarding_type:
            onboarding_price = max(grouping_one_total * 1, 3000.00)
        else:
            onboarding_price = max(grouping_one_total * 2, 3000.00)

    if onboarding_price != "Not Required":
        st.write(f"Onboarding Price: ${onboarding_price:.2f}")
    else:
        st.write(f"Onboarding Price: {onboarding_price}")

# Discount Section
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Discount</h2>',
    unsafe_allow_html=True
)
discount_option = st.selectbox(
    "Select Discount Option",
    ["No Discount", "30 Days Free", "Percentage Discount"]
)

if discount_option == "Percentage Discount":
    discount_percentage = st.number_input(
        "Enter Discount Percentage",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=0.1
    ) / 100.0
else:
    discount_percentage = 0.0

# --- Cost Calculation ---
raw_ariento_cost = sum(
    quantity * (
        filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].values[0]
        if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].empty else 0.0
    ) for seat, quantity in seat_types.items()
)

raw_microsoft_cost = sum(
    quantity * (
        microsoft_licenses.loc[microsoft_licenses["License"] == lic, "Price"].values[0]
        if not microsoft_licenses.loc[microsoft_licenses["License"] == lic, "Price"].empty else 0.0
    ) for lic, quantity in microsoft_seats.items()
)

if ariento_plan == "Enclave One":
    ariento_cost_label = "Annual Ariento Cost (Up Front)"
    microsoft_cost_label = "Annual Microsoft License Costs (Up Front)"
else:
    ariento_cost_label = "Monthly Ariento Cost (Recurring)"
    microsoft_cost_label = "Monthly Microsoft/Other License Costs (Recurring)"

# --- Discount Logic ---
# For "30 Days Free": discount applies to Seat Types, Microsoft Licenses, and Onboarding.
# For "Percentage Discount": discount applies ONLY to Seat Types.
discount_onboarding = 0
if discount_option == "30 Days Free":
    discount_ariento = raw_ariento_cost / 12
    discount_microsoft = raw_microsoft_cost / 12
    if onboarding_type != "None" and onboarding_price != "Not Required":
         discount_onboarding = onboarding_price / 12
         onboarding_price = onboarding_price - discount_onboarding
         onboarding_price = max(onboarding_price, 3000.00)
elif discount_option == "Percentage Discount":
    discount_ariento = raw_ariento_cost * discount_percentage
    discount_microsoft = 0
    # No discount applied to Onboarding for Percentage Discount.
else:
    discount_ariento = 0
    discount_microsoft = 0

final_ariento_cost = raw_ariento_cost - discount_ariento
final_microsoft_cost = raw_microsoft_cost - discount_microsoft

# --- Display Separate Costs ---
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Separate Costs</h2>',
    unsafe_allow_html=True
)
onboarding_display = onboarding_price if onboarding_price == "Not Required" else f"${onboarding_price:.2f}"
st.write(f"### {ariento_cost_label}: ${final_ariento_cost:.2f}")
st.write(f"### {microsoft_cost_label}: ${final_microsoft_cost:.2f}")
if onboarding_price != "Not Required":
    st.write(f"### Ariento Onboarding (One-Time): {onboarding_display}")

# --- Summary Table ---
st.markdown(
    '<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Summary of Selected Items</h2>',
    unsafe_allow_html=True
)
data = []

# Add Seat Types (line items)
for seat, quantity in seat_types.items():
    price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].values[0] \
            if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Seat Type", seat, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add Microsoft/Other Licenses (line items)
for lic, quantity in microsoft_seats.items():
    price = microsoft_licenses.loc[microsoft_licenses["License"] == lic, "Price"].values[0] \
            if not microsoft_licenses.loc[microsoft_licenses["License"] == lic, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Microsoft License", lic, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add Onboarding row only if applicable
if onboarding_price != "Not Required":
    data.append(["Onboarding", onboarding_type, 1, f"${onboarding_price:.2f}", f"${onboarding_price:.2f}"])

# Add Discount row if applicable; note that for Percentage Discount only the Seat Type discount is applied.
if discount_option != "No Discount":
    total_discount = discount_ariento + discount_microsoft + discount_onboarding
    if discount_option == "30 Days Free":
        discount_label = "30 Days Free"
    else:
        discount_label = f"{discount_percentage * 100:.1f}% Discount"
    data.append(["Discount", discount_label, "-", f"-${total_discount:.2f}", f"-${total_discount:.2f}"])

summary_df = pd.DataFrame(data, columns=["Category", "Item", "Quantity", "Price Per Unit", "Total Cost"])
# Force the DataFrame to strings to avoid serialization issues.
summary_df = summary_df.astype(str)
st.table(summary_df.style.hide(axis='index'))

# --- Display Date, Time, and Legal Notice on Main Page ---
date_time_now = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
st.markdown(
    f'<p style="font-family: Arial; font-size: 12pt; color: #3265A7;">Date and Time: {date_time_now}</p>',
    unsafe_allow_html=True
)
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

# --- CSV Download ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv_data = convert_df_to_csv(summary_df)
st.download_button(
    label="Download Summary as CSV",
    data=csv_data,
    file_name="summary_table.csv",
    mime="text/csv"
)

# --- PDF Generation Function ---
def generate_pdf(df, company_name):
    buffer = BytesIO()
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Add Logo (with aspect ratio maintained)
    try:
        logo_path = "Ariento Logo Blue.png"
        pil_image = PILImage.open(logo_path)
        original_width, original_height = pil_image.size
        max_width, max_height = 150, 75  # maximum dimensions for the logo
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
        elements.append(Spacer(1, 12))
    except Exception as e:
        elements.append(Paragraph(f"Error loading logo: {str(e)}", styles['Normal']))

    # Add Company Name and Date/Time
    elements.append(Paragraph(f"Company: {company_name}", styles['Normal']))
    current_datetime = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
    elements.append(Paragraph(f"Date and Time: {current_datetime}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Display Separate Costs
    elements.append(Paragraph(f"{ariento_cost_label}: ${final_ariento_cost:.2f}", styles['Heading2']))
    elements.append(Paragraph(f"{microsoft_cost_label}: ${final_microsoft_cost:.2f}", styles['Heading2']))
    if onboarding_price != "Not Required":
        onboarding_str = f"${onboarding_price:.2f}"
        elements.append(Paragraph(f"Ariento Onboarding (One-Time): {onboarding_str}", styles['Heading2']))

    if discount_option != "No Discount":
        if discount_option == "30 Days Free":
            discount_text = "30 Days Free"
        else:
            discount_text = f"{discount_percentage * 100:.1f}% Discount"
        elements.append(Paragraph(f"Discount: {discount_text}", styles['Heading2']))

    elements.append(Spacer(1, 12))

    # Define a ParagraphStyle for wrapping table cell text
    wrap_style = ParagraphStyle(
        name="WrappedText",
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        wordWrap="LTR",
    )

    # Prepare table data with header row
    table_data = [list(df.columns)]
    for row in df.values.tolist():
        row[1] = Paragraph(str(row[1]), wrap_style)
        table_data.append(row)

    # Create and style the table
    table = Table(table_data, colWidths=[100, 150, 50, 100, 100])
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E8A33D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(table_style)
    elements.append(table)

    elements.append(Spacer(1, 12))
    # Append Legal Notice at the bottom of the PDF
    legal_notice = (
        "Legal Notice: This quote is valid for 30 days from the date of issuance. Prices are subject to change after this period "
        "and are contingent upon availability and market conditions at the time of order placement. This quote does not constitute "
        "a binding agreement and is provided for informational purposes only. Terms and conditions may apply. Please contact us with "
        "any questions or for further clarification."
    )
    elements.append(Paragraph(legal_notice, styles['Normal']))

    pdf_doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

# PDF Download Button
pdf_bytes = generate_pdf(summary_df, company_name if company_name else "Company_Name")
st.download_button(
    label="Download Summary as PDF",
    data=pdf_bytes,
    file_name=f"{sanitize_filename(company_name) if company_name else 'quote'}_quote.pdf",
    mime="application/pdf"
)
