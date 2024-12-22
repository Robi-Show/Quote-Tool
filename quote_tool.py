import streamlit as st
import pandas as pd
import datetime

# Load Excel File
def load_data():
    excel_file = "Ariento Pricing 2025.xlsx"
    ariento_plans = pd.read_excel(excel_file, sheet_name="Ariento Plans")
    license_types = pd.read_excel(excel_file, sheet_name="Ariento License Type")
    microsoft_licenses = pd.read_excel(excel_file, sheet_name="Microsoft Seat Licenses")
    additional_licenses = pd.read_excel(excel_file, sheet_name="Additional Licenses")
    return ariento_plans, license_types, microsoft_licenses, additional_licenses

# Load data
ariento_plans, license_types, microsoft_licenses, additional_licenses = load_data()

from PIL import Image

# Title and Description
logo = Image.open("Ariento Logo Blue.png")  # Replace 'logo.png' with the path to your logo file
st.image(logo, width=200)
st.markdown('<h1 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Ariento Quote Tool</h1>', unsafe_allow_html=True)
st.markdown('<p style="font-family: Arial; font-size: 12pt; line-height: 1.15; color: #3265A7;">This tool helps you generate a quote based on Ariento Pricing 2025.</p>', unsafe_allow_html=True)
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

# Step 2: Microsoft Licenses
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Microsoft Licenses</h2>', unsafe_allow_html=True)
filtered_microsoft = microsoft_licenses[microsoft_licenses["Plan"] == ariento_plan]
microsoft_seats = {}

# Dynamic Microsoft License Selection
microsoft_license_options = list(filtered_microsoft["License"].unique()) + ["Other"]
row_counter = 0

while True:
    cols = st.columns(2)
    with cols[0]:
        microsoft_license = st.selectbox(
            "Select a Microsoft License",
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
        if other_license == "Select License":
            continue
        microsoft_license = other_license

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

onboarding_price = 0.0
if onboarding_type in ["None", "Other"]:
    onboarding_price = st.number_input("Enter Onboarding Price", min_value=0.0, value=0.0)
else:
    grouping_one_total = sum(
        quantity * (
            filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
            if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
        ) for seat_type, quantity in seat_types.items()
    )
    if "50% off" in onboarding_type:
        onboarding_price = grouping_one_total * 1
    else:
        onboarding_price = grouping_one_total * 2

st.write(f"Onboarding Price: ${onboarding_price:.2f}")

# Total Calculation
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Total Quote Cost</h2>', unsafe_allow_html=True)
total_cost = onboarding_price

total_cost += sum(
    quantity * (
        filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0]
        if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
    ) for seat_type, quantity in seat_types.items()
)
total_cost += sum(
    quantity * (
        filtered_microsoft.loc[filtered_microsoft["License"] == license, "Price"].values[0]
        if not filtered_microsoft.loc[filtered_microsoft["License"] == license, "Price"].empty else 0.0
    ) for license, quantity in microsoft_seats.items()
)

st.write(f"### Total Cost: ${total_cost:.2f}")

# Summary Table
st.markdown('<h2 style="font-family: Arial; font-size: 14pt; color: #E8A33D;">Summary of Selected Items</h2>', unsafe_allow_html=True)
data = []

# Add seat types
for seat_type, quantity in seat_types.items():
    price = filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].values[0] if not filtered_licenses.loc[filtered_licenses["Seat Type"] == seat_type, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Seat Type", seat_type, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add Microsoft licenses
for license, quantity in microsoft_seats.items():
    price = filtered_microsoft.loc[filtered_microsoft["License"] == license, "Price"].values[0] if not filtered_microsoft.loc[filtered_microsoft["License"] == license, "Price"].empty else 0.0
    cost = quantity * price
    data.append(["Microsoft License", license, quantity, f"${price:.2f}", f"${cost:.2f}"])

# Add onboarding
if onboarding_price > 0:
    data.append(["Onboarding", onboarding_type, 1, f"${onboarding_price:.2f}", f"${onboarding_price:.2f}"])

# Display table
import pandas as pd

# Display current date and time
date_time_now = datetime.datetime.now().strftime('%B %d, %Y %H:%M:%S')
st.markdown(f'<p style="font-family: Arial; font-size: 12pt; color: #3265A7;">Date and Time: {date_time_now}</p>', unsafe_allow_html=True)
summary_df = pd.DataFrame(data, columns=["Category", "Item", "Quantity", "Price Per Unit", "Total Cost"])
st.table(summary_df.style.hide(axis='index'))

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