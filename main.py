import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app, auth,exceptions
import cv2
import base64
import preprocessor
import helper
import webbrowser
import preprocessor as pp


# Function to initialize Firebase app
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("cybercrime-4ad9a-6808af91116c.json")
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()
init_firebase()

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()



# Assuming authenticate_user is a placeholder for actual authentication logic
def authenticate_user(users, username, password):
    return (username in users) and (users[username] == password)


if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Home"
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

page = st.sidebar.selectbox("Select", ["Home", "Login", "Sign Up", "Chat Analyzer"])

if page == "Home":
    st.title("Welcome to the WhatsApp Chat Analyzer!")
    st.markdown("""
            This app helps you analyze your WhatsApp chats including spam detection.
            Please navigate to the **Login** or **Sign Up** page to get started.
        """)

elif page == "Login":
    if st.session_state['authenticated']:
        st.warning("You are already logged in.")
    else:
        st.title("Login Page")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            try:
                # Attempt to get the user by email
                user = auth.get_user_by_email(email)
                if user:
                    # Assuming successful authentication
                    st.session_state['authenticated'] = True
                    st.success(f"Login successful: {user.email}")

                    st.session_state['current_page'] = "Chat Analyzer"
                    st.experimental_rerun()
            except exceptions.NotFoundError:
                st.error("User not found.")
            except Exception as e:
                st.error(f"Login failed: {str(e)}")


elif page == "Sign Up":
    st.title("Sign Up Page")
    email = st.text_input("Email Address")
    username = st.text_input("Choose a username")
    password = st.text_input("Choose a password", type="password")
    confirm_password = st.text_input("Confirm password", type="password")

    if st.button("Sign Up"):
        try:
            user = auth.create_user(email=email, password=password, uid=username)
            st.success("Account created successfully!")
            st.markdown("Please Login using your E-mail and Password ")
            st.balloons()
        except Exception as e:
            st.error(f"Failed to create account: {e}")

elif page == "Chat Analyzer":
    def open_whatsapp_web():
        url = "https://web.whatsapp.com/"
        webbrowser.open(url)


    # Streamlit UI
    st.title("WhatsApp Web Integration")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Open WhatsApp Web"):
            open_whatsapp_web()
    if st.session_state['authenticated']:
        st.title("WhatsApp Chat Analyzer")
        # Place the content of chat_analyzer_page() here
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            data = bytes_data.decode('utf-8')
            df = preprocessor.preprocess(data)

            st.dataframe(df)

            user_list = df["user"].unique().tolist()
            user_list.remove("group_notification")
            user_list.sort()
            user_list.insert(0, "Overall")

            selected_user = st.sidebar.selectbox("Show analysis wrt", user_list)

            if st.sidebar.button("Show Analysis"):
                num_messages, words, num_media_messages, num_links = helper.fetch_stats(selected_user, df)
                st.title("Top Statistics")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.header("Total Messages")
                    st.title(num_messages)

                with col2:
                    st.header("Total Words")
                    st.title(words)

                with col3:
                    st.header("Media Shared")
                    st.title(num_media_messages)

                with col4:
                    st.header("Links Shared")
                    st.title(num_links)

                st.title('Shared Links in Chat')
                links_df = helper.shared_links_df_simple(df)

                if not links_df.empty:
                    st.dataframe(links_df)
                else:
                    st.write("No links shared.")

                # monthly timeline
                st.title("Monthly Timeline")
                timeline = helper.monthly_timeline(selected_user, df)
                fig, ax = plt.subplots()
                ax.plot(timeline['time'], timeline['message'], color='green')
                plt.xticks(rotation='vertical')
                st.pyplot(fig)

                # daily timeline
                st.title("Daily Timeline")
                daily_timeline = helper.daily_timeline(selected_user, df)
                fig, ax = plt.subplots()
                ax.plot(daily_timeline['only_time'], daily_timeline['message'], color='red')
                plt.xticks(rotation='vertical')
                st.pyplot(fig)

                # finding the busiest users in the group(Group level)
                if selected_user == 'Overall':
                    st.title('Most Busy Users')
                    x, new_df = helper.most_busy_users(df)
                    fig, ax = plt.subplots()

                    col1, col2 = st.columns(2)

                    with col1:
                        ax.bar(x.values, x.index, color='green')
                        plt.xticks(rotation='vertical')
                        st.pyplot(fig)

                    with col2:
                        st.dataframe(new_df)

                # WordCloud
                st.title("Wordcloud")
                df_wc = helper.create_wordcloud(selected_user, df)
                fig, ax = plt.subplots()
                ax.imshow(df_wc)
                st.pyplot(fig)

                # most common words
                most_common_df = helper.most_common_words(selected_user, df)

                fig, ax = plt.subplots()

                ax.barh(most_common_df[0], most_common_df[1])
                plt.xticks(rotation='vertical')

                st.title('Most common words')
                st.pyplot(fig)

                 # Show Detection


            if st.sidebar.button("Detect Spam"):
                st.title("Detected Spam")
                clean_data_df=preprocessor.clean_data(df)
                detection_df = preprocessor.apply_spam_classification(clean_data_df)
                result_df = detection_df[detection_df['is_spam'] == "Yes"][['user', 'date', 'message', 'spam_keywords', 'is_spam']]

                if not result_df.empty:
                    st.error("⚠️ Spam detected ! ")
                    st.error("Please review the highlighted messages below.")

                # Display results
                    def highlight_spam(row):
                    # Apply red background to 'is_spam' column if spam, otherwise green
                     return ['background-color: red' if v == "Yes" else '' for v in row]

                # Apply the highlighting function on the DataFrame and display it
                    st.dataframe(result_df.style.apply(highlight_spam, subset=['is_spam']), height=600)
                else:
                    st.success("✅ No spam messages detected.")


    else:
        st.warning("You need to login to access this page.")
