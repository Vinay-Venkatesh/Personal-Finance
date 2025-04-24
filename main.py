import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import os

# Streamlit page title
st.set_page_config(page_title="Personal Finance", page_icon="💰", layout="wide")
category_file = "categories.json"

if "categories" not in st.session_state:
    # session state will be stored in a variable called categories to persist the added categories.
    st.session_state.categories = {
        "Uncategorized": []
    }

# load the categories from the json file if its exists.
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

# to store the categories created from the UI into a file from the session state
def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

# Categorize transactions
def categorize_transactions(df):
    # default all the data is set to Uncategorized
    df["Category"] = "Uncategorized"

    # Apply categories 
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Narration"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category
    
    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        # removing the leading and trailing whitespaces in cols.
        df.columns = [col.strip() for col in df.columns]
        
        # converting the amount to string & removing "," & nan types & converting it to float
        # clean and convert amounts, handling empty strings and actual "nan" text values
        df["Withdrawal Amt."] = (
            df["Withdrawal Amt."]
            .astype(str)
            .str.replace(",", "")
            .replace(["", "nan", "NaN"], 0)
            .astype(float)
        )

        df["Deposit Amt."] = (
            df["Deposit Amt."]
            .astype(str)
            .str.replace(",", "")
            .replace(["", "nan", "NaN"], 0)
            .astype(float)
        )

        # converting date to valid date time format
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%y")
        
        # Categorize the transactions
        return categorize_transactions(df)

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# save categories
def add_keyword_to_category(category,keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def main():

    st.title("Personal Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your bank statement as csv file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            debits_df = df[df["Withdrawal Amt."] > 0].copy() # gives col only of Debit 
            credits_df = df[df["Deposit Amt."]> 0].copy() # gives col only of Credit 

            st.session_state.debits_df = debits_df.copy()
            st.session_state.credits_df = credits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payment (Credits)"])
            with tab1:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        # adding a new_category as array element to session state
                        st.session_state.categories[new_category] = []
                        save_categories()
                        
                        # reload the categories immediately after its added
                        st.rerun()
                
                st.subheader("OutFlow Summary")
                total_debit = debits_df["Withdrawal Amt."].sum()
                st.metric("Total Outflow", f"{total_debit:,.2f} INR")

                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    # col to filter and show
                    st.session_state.debits_df[["Date", "Narration", "Withdrawal Amt.", "Category"]],
                    
                    # Formatting the cols
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Withdrawal Amt.": st.column_config.NumberColumn("Debit", format="%.2f INR"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True, # full screen
                    key="debit_category_editor"
                )

                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        # If there was no change made to the Category - Continue
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        # if there was category change made
                        # update the category in the details 
                        # save the category
                        details = row["Narration"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader("Expense Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Withdrawal Amt."].sum().reset_index()
                category_totals = category_totals.sort_values("Withdrawal Amt.", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        "Withdrawal Amt.": st.column_config.NumberColumn("Debit", format="%.2f INR")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                # generating pie chart using plotly express
                debit_figure = px.pie(
                    category_totals,
                    values="Withdrawal Amt.",
                    names="Category",
                    title="Debits by Category"
                )

                st.plotly_chart(debit_figure, use_container_width=True)

            with tab2:
                st.subheader("Inflow Summary")
                total_credit = credits_df["Deposit Amt."].sum()
                st.metric("Total Inflow", f"{total_credit:,.2f} INR")

                edited_df = st.data_editor(
                    # col to filter and show
                    st.session_state.credits_df[["Date", "Narration", "Deposit Amt.", "Category"]],
                    
                    # Formatting the cols
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Deposit Amt.": st.column_config.NumberColumn("Credit", format="%.2f INR"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True, # full screen
                    key="credit_category_editor"
                )

                save_button = st.button("Apply Category", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        # There was no change made to the Category - Continue
                        if new_category == st.session_state.credits_df.at[idx, "Category"]:
                            continue
                        # if there was category change made
                        # update the category in the details 
                        # save the category
                        details = row["Narration"]
                        st.session_state.credits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader("Credit Summary")
                category_totals = st.session_state.credits_df.groupby("Category")["Deposit Amt."].sum().reset_index()
                category_totals = category_totals.sort_values("Deposit Amt.", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        "Deposit Amt.": st.column_config.NumberColumn("Credit", format="%.2f INR")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                # generating pie chart using plotly express
                credit_figure = px.pie(
                    category_totals,
                    values="Deposit Amt.",
                    names="Category",
                    title="Credits by Category"
                )

                st.plotly_chart(credit_figure, use_container_width=True)                


if __name__ == "__main__":
    main()