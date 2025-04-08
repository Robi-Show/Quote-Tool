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

# Custom CSS to widen select boxes
st.markdown("""
    <style>
    .stSelectbox > div > div > div {
        min-width: 600px;
    }
    </style>
    """, unsafe_allow_html=True)

# ----------------------------------------
# Data Loading Functions
# ----------------------------------------
def load_data():
    # Load Ariento Pricing data
    ariento_url = "https://raw.githubusercontent.com/Robi-Show/Quote-Tool/main/Ariento%20Pricing%202025.xlsx"
    response = requests.get(ariento_url)
    if response.status_code != 200:
        st.error("Failed to fetch the Ariento Pricing Excel file. Please check the file URL.")
        st.stop()
    ariento_file = BytesIO(response.content)
    try:
        ariento_plans = pd.read_excel(ariento_file, sheet_name="Ariento Plans")
        license_types = pd.read_excel(ariento_file, sheet_name="Ariento License Type")
    except KeyError as e:
        st.error(f"Missing sheet or column in Ariento Pricing file: {e}")
        st.stop()

    # Load Service Catalogue data
    service_catalog_url = "https://raw.githubusercontent.com/Robi-Show/Quote-Tool/main/Service+Catalogue.xlsx"
    response_service = requests.get(service_catalog_url)
    if response_service.status_code != 200:
        st.error("Failed to fetch the Service Catalogue Excel file. Please check the file URL.")
        st.stop()
    service_file = BytesIO(response_service.content)
    try:
        all_sheets = pd.read_excel(service_file, sheet_name=None)
        available_sheet_names = list(all_sheets.keys())
        cisco_meraki = None
        m365_sheet = None
        # Remove spaces and lowercase sheet names for robust matching
        for sheet_name, df in all_sheets.items():
            lower_name = sheet_name.lower().replace(" ", "")
            if "ciscomeraki" in lower_name:
                cisco_meraki = df
            if "m365" in lower_name:
                m365_sheet = df
        if cisco_meraki is None or m365_sheet is None:
            st.error("One or more required sheets (Cisco Meraki, M365) not found in Service+Catalogue.xlsx. Available sheets: " + ", ".join(available_sheet_names))
            st.stop()
        m365 = m365_sheet
    except Exception as e:
        st.error(f"Error loading Service Catalogue Excel file: {e}")
        st.stop()

    def filter_sheet(df, required_cols):
        df.columns = df.columns.str.strip()
        for col in required_cols:
            if col in df.columns:
                df = df.dropna(subset=[col])
        if "Price" in df.columns:
            df = df[~df["Price"].astype(str).str.strip().isin(["Quote Only", "Custom", "Ad Hoc as needed"])]
        for col in ["Notes", "Minimum Specs"]:
            if col in df.columns:
                df = df.drop(columns=[col])
        return df

    cisco_meraki = filter_sheet(cisco_meraki, ["Price"])
    # For M365, use "Term Commit" exactly as in the Excel file.
    m365 = filter_sheet(m365, ["Billing Cycle", "Term Commit", "Price"])
    if "Segment" in m365.columns:
        m365 = m365[~m365["Segment"].isin(["Education", "Charity", "GCC-High GOV ONLY"])]
    
    return ariento_plans, license_types, cisco_meraki, m365

def get_default_segment(plan):
    if "GCC-H" in plan or "GCCH" in plan:
        return "GCC-High NON GOV"
    elif "GCC" in plan:
        return "GCC"
    elif "Commercial" in plan:
        return "Commercial"
    else:
        return None

# Load data
ariento_plans, license_types, cisco_meraki, m365 = load_data()

# ----------------------------------------
# Title, Logo, and Description
# ----------------------------------------
logo_url = "https://raw.githubusercontent.com/Robi-Show/Quote-Tool/main/Ariento%20Logo%20Blue.png"
response_logo = requests.get(logo_url)
if response_logo.status_code == 200:
    logo = Image.open(BytesIO(response_logo.content))
    st.image(logo, width=200)
else:
    st.error("Logo file not found. Please ensure 'Ariento Logo Blue.png' is in the repository.")

st.markdown('<h1 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Quote Tool</h1>', unsafe_allow_html=True)
st.markdown('<hr style="border: 1px solid #E8A33D;">', unsafe_allow_html=True)
st.markdown('<p style="font-family: Arial; font-size: 12pt; color: #3265A7;">This tool generates a quote based on Ariento Pricing and Service Catalogue data.</p>', unsafe_allow_html=True)

# ----------------------------------------
# Company Name & Business Model
# ----------------------------------------
company_name = st.text_input("Enter Company Name")
def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

st.markdown("### Business Model Selection")
business_model = st.radio("Select Business Model", options=["Enclave One", "Custom Enclave", "MSSP", "Third Party Resell"])

if business_model == "Enclave One":
    enclave_option = st.selectbox("Select Enclave One Option", ["Enclave One (GCC)", "Enclave One (GCC-H)"])
elif business_model == "Custom Enclave":
    custom_segment = st.selectbox("Select Custom Enclave Segment", ["Commercial", "GCC", "GCC-H"])
    if custom_segment == "Commercial":
        custom_option = st.selectbox("Select Option", ["Professional", "Enterprise"])
    elif custom_segment == "GCC":
        custom_option = st.selectbox("Select Option", ["Turnkey CMMC Level 2 Plan (GCC)", "Turnkey CMMC Level 3 Plan (GCC)"])
    elif custom_segment == "GCC-H":
        custom_option = st.selectbox("Select Option", ["Turnkey CMMC Level 2 Plan (GCC-High)", "Turnkey CMMC Level 3 Plan (GCC-High)"])
elif business_model == "MSSP":
    mssp_option = "MSSP"
elif business_model == "Third Party Resell":
    tpr_option = "Third Party Resell"

if business_model != "Third Party Resell":
    if business_model == "Enclave One":
        ariento_plan = enclave_option
    elif business_model == "Custom Enclave":
        ariento_plan = custom_option
    elif business_model == "MSSP":
        ariento_plan = "MSSP"
    st.write(f"Selected Ariento Plan: {ariento_plan}")
else:
    ariento_plan = None

today_str = datetime.datetime.now().strftime("%Y%m%d")
if company_name:
    file_prefix = f"{company_name}-{business_model}-{today_str}"
else:
    file_prefix = "quote"

# ----------------------------------------
# Ariento Licenses Section (Hidden if Third Party Resell)
# Billing Cycle: For Enclave One with "GCC-H" force Annual; else allow both.
# Add Tooltip link "See Types"
# ----------------------------------------
if business_model != "Third Party Resell":
    st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Licenses</h2>', unsafe_allow_html=True)
    if business_model == "Enclave One" and ariento_plan and ("GCC-H" in ariento_plan or "GCCH" in ariento_plan):
        ariento_billing_options = ["Annual"]
    else:
        ariento_billing_options = ["Monthly", "Annual"]
    ariento_billing = st.radio("Ariento Billing Cycle", options=ariento_billing_options, index=0, key="ariento_billing")
    filtered_licenses = license_types[license_types["Plan"] == ariento_plan]
    
    # Set up the tooltip link based on business model
    if business_model in ["Custom Enclave", "MSSP"]:
        see_types_link = '<a href="https://www.ariento.com/user-types/" target="_blank" title="See Types">See Types</a>'
    elif business_model == "Enclave One":
        see_types_link = '<a href="https://www.ariento.com/enclave-one-user-types" target="_blank" title="See Types">See Types</a>'
    else:
        see_types_link = ""
    st.markdown(f"<strong>Select a Seat Type</strong> {see_types_link}", unsafe_allow_html=True)
    
    seat_types = {}
    seat_type_options = filtered_licenses["Seat Type"].unique()
    while True:
        seat_type = st.selectbox("", ["Select Seat Type"] + list(seat_type_options), key=f"seat_type_{len(seat_types)}")
        if seat_type == "Select Seat Type" or seat_type == "":
            break
        quantity = st.number_input(f"Quantity for {seat_type}", min_value=0, value=1, key=f"seat_qty_{len(seat_types)}")
        if quantity > 0:
            price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
            cost = quantity * price
            st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
            seat_types[seat_type] = quantity
else:
    seat_types = {}

# ----------------------------------------
# M365 Section (same font as Ariento Licenses)
# ----------------------------------------
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">M365 Licenses</h2>', unsafe_allow_html=True)
if business_model != "Third Party Resell":
    default_segment = get_default_segment(ariento_plan)
else:
    default_segment = None

if ariento_plan and ("GCC-H" in ariento_plan or "GCCH" in ariento_plan):
    m365_term_options = ["Annual"]
    m365_billing_options = ["Annual"]
else:
    m365_term_options = ["Annual", "Monthly"]
    m365_billing_options = ["Annual", "Monthly"]

col_m365_1, col_m365_2 = st.columns(2)
with col_m365_1:
    m365_term = st.radio("M365 Term Commitment", options=m365_term_options, index=0, key="m365_term")
with col_m365_2:
    m365_billing = st.radio("M365 Billing Cycle", options=m365_billing_options, index=0, key="m365_billing")

if default_segment:
    m365_filtered = m365[m365["Segment"].astype(str).str.strip() == default_segment]
else:
    m365_filtered = m365.copy()

m365_filtered = m365_filtered[
    (m365_filtered["Term Commit"].astype(str).str.strip() == m365_term) &
    (m365_filtered["Billing Cycle"].astype(str).str.strip() == m365_billing)
]

m365_options = m365_filtered["SkuTitle"].unique()
m365_selections = []
while True:
    cols = st.columns(2)
    with cols[0]:
        selected_sku = st.selectbox("Select an M365 License", ["Select License"] + list(m365_options), key=f"m365_sku_{len(m365_selections)}")
    if selected_sku == "Select License" or selected_sku == "":
        break
    with cols[1]:
        quantity = st.number_input(f"Quantity for {selected_sku}", min_value=0, value=1, key=f"m365_qty_{len(m365_selections)}")
    if quantity > 0:
        row_match = m365_filtered[m365_filtered["SkuTitle"] == selected_sku]
        if not row_match.empty:
            price = row_match["Price"].values[0]
            productID = row_match["ProductId"].values[0]
            skuId = row_match["SkuId"].values[0]
            cost = price * quantity
            st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
            m365_selections.append({
                "SkuTitle": selected_sku,
                "ProductID": productID,
                "SkuId": skuId,
                "Price": price,
                "Quantity": quantity
            })
        else:
            st.warning("No matching row found for this SkuTitle with the selected Term/Billing combination.")

# ----------------------------------------
# Cisco Meraki Section (same font as Ariento Licenses)
# ----------------------------------------
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Cisco Meraki Licenses</h2>', unsafe_allow_html=True)
meraki_options = cisco_meraki["Description"].unique()
meraki_selections = []
while True:
    cols = st.columns(2)
    with cols[0]:
        selected_desc = st.selectbox("Select a Cisco Meraki License (by Description)", ["Select License"] + list(meraki_options), key=f"meraki_desc_{len(meraki_selections)}")
    if selected_desc == "Select License" or selected_desc == "":
        break
    with cols[1]:
        quantity = st.number_input(f"Quantity for {selected_desc}", min_value=0, value=1, key=f"meraki_qty_{len(meraki_selections)}")
    if quantity > 0:
        row_match = cisco_meraki[cisco_meraki["Description"] == selected_desc]
        if not row_match.empty:
            price = row_match["Price"].values[0]
            sku_val = row_match["SKU"].values[0]
            cost = price * quantity
            st.write(f"Price: ${price:.2f} | Quantity: {quantity} | Cost: ${cost:.2f}")
            meraki_selections.append({
                "Description": selected_desc,
                "SKU": sku_val,
                "Price": price,
                "Quantity": quantity
            })
        else:
            st.warning("No matching row found for this description.")

# ----------------------------------------
# Onboarding Section (same font as Ariento Licenses)
# ----------------------------------------
if business_model != "Third Party Resell":
    st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Onboarding</h2>', unsafe_allow_html=True)
    if business_model == "Enclave One":
        onboarding_type = "Not Required"
        onboarding_price = "Not Required"
        st.write("Onboarding Price: Not Required")
    else:
        onboarding_type = st.selectbox("Select Onboarding Payment Type", ["One Time Onboarding Payment", "Other", "None"])
        if onboarding_type == "None":
            onboarding_price = "Not Required"
        elif onboarding_type == "Other":
            onboarding_price = st.number_input("Enter Onboarding Price", min_value=0.0, value=3000.0)
        else:
            grouping_one_total = sum(
                qty * (license_types.loc[
                    (license_types["Plan"] == ariento_plan) & (license_types["Seat Type"] == seat),
                    "Price"
                ].values[0] if not license_types.loc[
                    (license_types["Plan"] == ariento_plan) & (license_types["Seat Type"] == seat),
                    "Price"
                ].empty else 0.0)
                for seat, qty in seat_types.items()
            )
            raw_onboarding = max(2 * grouping_one_total, 3000)
            onboarding_price = raw_onboarding
        st.write(f"Onboarding Price: {onboarding_price}")
else:
    onboarding_price = 0

# ----------------------------------------
# Discount Options (applied only to Ariento Licenses and Onboarding)
# ----------------------------------------
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Discount</h2>', unsafe_allow_html=True)
discount_option = st.selectbox("Select Discount Option", ["No Discount", "30 Days Free", "10% Discount", "Percentage Discount"])
if discount_option == "10% Discount":
    discount_percentage = 0.10
elif discount_option == "Percentage Discount":
    discount_percentage = st.number_input("Enter Discount Percentage", min_value=0.0, max_value=100.0, value=10.0, step=0.1) / 100.0
else:
    discount_percentage = 0.0

# ----------------------------------------
# Final Cost Calculation
# ----------------------------------------
if business_model != "Third Party Resell":
    monthly_ariento_cost = sum(
        qty * (license_types.loc[
            (license_types["Plan"] == ariento_plan) & (license_types["Seat Type"] == seat),
            "Price"
        ].values[0] if not license_types.loc[
            (license_types["Plan"] == ariento_plan) & (license_types["Seat Type"] == seat),
            "Price"
        ].empty else 0.0)
        for seat, qty in seat_types.items()
    )
    if ariento_billing == "Annual" and ("GCC-H" not in ariento_plan and "GCCH" not in ariento_plan):
        raw_ariento_cost = 12 * ariento_base_cost
    else:
        raw_ariento_cost = ariento_base_cost
else:
    raw_ariento_cost = 0

raw_m365_cost = sum(
    msel["Price"] * msel["Quantity"] for msel in m365_selections
) if m365_selections else 0

raw_meraki_cost = sum(
    msel["Price"] * msel["Quantity"] for msel in meraki_selections
) if meraki_selections else 0

microsoft_cost = raw_m365_cost
service_cost = raw_meraki_cost

if business_model != "Third Party Resell" and business_model != "Enclave One":
    raw_onboarding = max(2 * raw_ariento_cost / (12 if ariento_billing == "Annual" else 1), 3000)
else:
    raw_onboarding = 0

if discount_option != "No Discount":
    discount_ariento = discount_percentage * raw_ariento_cost
    new_ariento_cost = raw_ariento_cost - discount_ariento

    if raw_onboarding > 0:
        discount_onboarding = discount_percentage * raw_onboarding
        new_onboarding_price = raw_onboarding - discount_onboarding
        if new_onboarding_price < 3000:
            new_onboarding_price = 3000
    else:
        discount_onboarding = 0
        new_onboarding_price = raw_onboarding
else:
    new_ariento_cost = raw_ariento_cost
    new_onboarding_price = raw_onboarding
    discount_ariento = 0
    discount_onboarding = 0

if ariento_plan is not None and (( "GCC-H" in ariento_plan or "GCCH" in ariento_plan) or (m365_billing == "Annual")):
    microsoft_label = "Microsoft Licenses Costs (Annual Recurring)"
else:
    microsoft_label = "Microsoft Licenses Costs (Monthly Recurring)"

# ----------------------------------------
# Display Separate Costs
# ----------------------------------------
if new_ariento_cost > 0:
    st.markdown(f"### Ariento Licenses Cost ({ariento_billing} Recurring): ${new_ariento_cost:.2f}")
if microsoft_cost > 0:
    st.markdown(f"### {microsoft_label}: ${microsoft_cost:.2f}")
if service_cost > 0:
    st.markdown(f"### Service License Costs (Recurring): ${service_cost:.2f}")

# ----------------------------------------
# Build Summary Table
# ----------------------------------------
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Summary of Selected Items</h2>', unsafe_allow_html=True)
data = []

if business_model != "Third Party Resell":
    for seat, qty in seat_types.items():
        # Get the base price from the license_types table
        price_row = license_types.loc[
            (license_types["Plan"] == ariento_plan) & (license_types["Seat Type"] == seat),
            "Price"
        ]
        price = price_row.values[0] if not price_row.empty else 0.0
        # If plan is NOT GCC-H and billing is annual, multiply by 12
        if ariento_billing == "Annual" and ("GCC-H" not in ariento_plan and "GCCH" not in ariento_plan):
            display_price = price * 12
        else:
            display_price = price
        cost = qty * display_price
        data.append(["Ariento License", seat, qty, f"${display_price:.2f}", f"${cost:.2f}"])

for msel in m365_selections:
    stitle = msel["SkuTitle"]
    productID = msel["ProductID"]
    skuId = msel["SkuId"]
    price = msel["Price"]
    qty = msel["Quantity"]
    cost = price * qty
    data.append(["M365", f"{stitle} (ProductId: {productID}, SkuId: {skuId})", qty, f"${price:.2f}", f"${cost:.2f}"])

for msel in meraki_selections:
    price = msel["Price"]
    qty = msel["Quantity"]
    cost = price * qty
    data.append(["Cisco Meraki", f"{msel['Description']} (SKU: {msel['SKU']})", qty, f"${price:.2f}", f"${cost:.2f}"])

if business_model != "Third Party Resell" and onboarding_price != "Not Required":
    data.append(["Onboarding", onboarding_type, 1, f"${new_onboarding_price:.2f}", f"${new_onboarding_price:.2f}"])

if discount_option != "No Discount":
    data.append(["Discount - Ariento", f"{discount_option} ({discount_percentage*100:.0f}%)", "-", f"-${discount_ariento:.2f}", f"-${discount_ariento:.2f}"])
    if raw_onboarding > 0:
        data.append(["Discount - Onboarding", f"{discount_option} ({discount_percentage*100:.0f}%)", "-", f"-${discount_onboarding:.2f}", f"-${discount_onboarding:.2f}"])

summary_df = pd.DataFrame(data, columns=["Category", "Item", "Quantity", "Price Per Unit", "Total Cost"])
summary_df = summary_df.astype(str)
st.table(summary_df.style.hide(axis='index'))

# ----------------------------------------
# Date, Time, and Legal Notice
# ----------------------------------------
date_time_now = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
st.markdown(f'<p style="font-family: Arial; font-size: 12pt; color: #3265A7;">Date and Time: {date_time_now}</p>', unsafe_allow_html=True)
st.markdown("""
<div style="font-family: Arial; font-size: 12pt; color: #3265A7; margin-top: 20px;">
    <strong>Legal Notice:</strong><br>
    This quote is valid for 30 days from the date of issuance. Prices are subject to change after this period 
    and are contingent upon availability and market conditions at the time of order placement. This quote does 
    not constitute a binding agreement and is provided for informational purposes only. Terms and conditions 
    may apply. Please contact us with any questions or for further clarification.
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# CSV Download
# ----------------------------------------
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv_data = convert_df_to_csv(summary_df)
st.download_button(
    label="Download Summary as CSV",
    data=csv_data,
    file_name=f"{sanitize_filename(file_prefix)}_quote.csv",
    mime="text/csv"
)

# ----------------------------------------
# PDF Generation
# ----------------------------------------
def generate_pdf(df, company_name):
    buffer = BytesIO()
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    try:
        logo_path = "https://raw.githubusercontent.com/Robi-Show/Quote-Tool/main/Ariento%20Logo%20Blue.png"
        response_logo = requests.get(logo_path)
        if response_logo.status_code == 200:
            pil_image = PILImage.open(BytesIO(response_logo.content))
            original_width, original_height = pil_image.size
            max_width, max_height = 150, 75
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
            elements.append(ReportLabImage(BytesIO(response_logo.content), width=resized_width, height=resized_height))
            elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph("Logo not found.", styles['Normal']))
    except Exception as e:
        elements.append(Paragraph(f"Error loading logo: {str(e)}", styles['Normal']))
    elements.append(Paragraph(f"Company: {company_name}", styles['Normal']))
    current_datetime = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
    elements.append(Paragraph(f"Date and Time: {current_datetime}", styles['Normal']))
    elements.append(Spacer(1, 12))
    if raw_ariento_cost > 0:
        elements.append(Paragraph(f"Ariento Licenses Cost ({ariento_billing} Recurring): ${new_ariento_cost:.2f}", styles['Heading2']))
    if microsoft_cost > 0:
        elements.append(Paragraph(f"{microsoft_label}: ${microsoft_cost:.2f}", styles['Heading2']))
    if service_cost > 0:
        elements.append(Paragraph(f"Service License Costs (Recurring): ${service_cost:.2f}", styles['Heading2']))
    if business_model != "Third Party Resell" and onboarding_price != "Not Required":
        elements.append(Paragraph(f"Ariento Onboarding (One-Time): ${new_onboarding_price:.2f}", styles['Heading2']))
    if discount_option != "No Discount":
        elements.append(Paragraph(f"Discount - Ariento: -${discount_ariento:.2f}", styles['Heading2']))
        if raw_onboarding > 0:
            elements.append(Paragraph(f"Discount - Onboarding: -${discount_onboarding:.2f}", styles['Heading2']))
    elements.append(Spacer(1, 12))
    wrap_style = ParagraphStyle(name="WrappedText", fontName="Helvetica", fontSize=10, leading=12, wordWrap="LTR")
    table_data = [list(df.columns)]
    for row in df.values.tolist():
        row[1] = Paragraph(str(row[1]), wrap_style)
        table_data.append(row)
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

pdf_bytes = generate_pdf(summary_df, company_name if company_name else "Company_Name")
st.download_button(label="Download Summary as PDF", data=pdf_bytes, file_name=f"{sanitize_filename(file_prefix)}_quote.pdf", mime="application/pdf")
