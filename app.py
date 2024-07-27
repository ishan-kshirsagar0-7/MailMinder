import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
import sqlite3
from dotenv import load_dotenv
load_dotenv()
import shutup  # to silence warnings
shutup.please()

# Setting up the Groq LLM
API_KEY = os.getenv("GROQ_API_KEY")
chat = ChatGroq(temperature=0, model_name="mixtral-8x7b-32768", api_key=API_KEY)

# Setting up a database connection
conn = sqlite3.connect('equipment.db')
cursor = conn.cursor()

# Setting up the RAG pipeline
embeddings = HuggingFaceEmbeddings()

# Loading and processing the FAQ data
loader = TextLoader("equipment_faq.md")
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

vectorstore = Chroma.from_documents(texts, embeddings)
retriever = vectorstore.as_retriever()

qa_chain = RetrievalQA.from_chain_type(
    llm=chat,
    chain_type="stuff",
    retriever=retriever
)

def classify_email(email_content):
    prompt = f"""
    Classify the following email into one of these categories: Inquiry, Review, Assistance Request, or Other.

    INSTRUCTIONS :

    1. If the text in the email intends to rent anything, or wants to know the price of a product, then the category is Inquiry. Usually such emails consists of common keyphrases like 'I want to rent' or 'Interested in renting' or anything similar.
    2. If the text in the email is providing some feedback, be it negative or positive, then the category is Review.
    3. If the text in the email is asking for help or assistance, then the category it belongs to is Assistance Request.
    4. If the email content does not fall into any of the above categories, then simply return the category as Other.
    5. Most importantly - YOUR OUTPUT SHOULD STRICTLY BE THE CATEGORY NAME, NOTHING ELSE, NOTHING EXTRA.
    
    Email: {email_content}
    
    Classification:
    """
    response = chat.invoke(prompt)
    return response.content.strip()

def handle_inquiry(email_content):
    extraction_prompt = f"""
    Extract the name of the product inside the given statement. Your output must strictly be just the name of the product, nothing else, nothing extra.

    EXAMPLE :

    Sentence : I want to rent an Axiom 1234 camera. Can you tell me the price?
    Product Name : Axiom 1234

    Sentence : How much for renting the Sony A800 lighting kit?
    Product Name : Sony A800

    Sentence : {email_content}
    Product Name :
    """
    extracted = chat.invoke(extraction_prompt)
    item_name = extracted.content
    
    cursor.execute("SELECT price, available FROM equipment WHERE name = ?", (item_name,))
    result = cursor.fetchone()
    
    if result:
        price, available = result
        if available:
            return f"The {item_name} is available for ${price:.2f}."
        else:
            cursor.execute("SELECT e.name FROM equipment e JOIN similar_items s ON e.id = s.similar_item_id WHERE s.item_id = (SELECT id FROM equipment WHERE name = ?)", (item_name,))
            similar_items = [row[0] for row in cursor.fetchall()]
            return f"The {item_name} is not available. Consider these similar items: {', '.join(similar_items)}."
    else:
        return "We couldn't find the requested item in our inventory."

def handle_review(email_content):
    sentiment_prompt = f"""
    Determine if the following review is positive or negative:
    
    Review: {email_content}
    
    Sentiment (Positive/Negative):
    """
    sentiment = chat.invoke(sentiment_prompt).content.strip().lower()
    
    if sentiment == "positive":
        return "Thank you for your positive review! We'd greatly appreciate it if you could share your experience on social media."
    else:
        return "We're sorry to hear about your experience. Our customer service team will contact you shortly to address your concerns. As a token of our appreciation, we'd like to offer you a gift voucher for your next rental."

def handle_assistance_request(email_content):
    response = qa_chain(email_content)
    if response['result']:
        return f"Here's a possible solution to your issue: {response['result']}"
    else:
        return "We couldn't find a solution to your issue. Our customer service team will contact you shortly to provide assistance."

def process_email(email_content):
    category = classify_email(email_content)
    
    if category == "Inquiry":
        return handle_inquiry(email_content)
    elif category == "Review":
        return handle_review(email_content)
    elif category == "Assistance Request":
        return handle_assistance_request(email_content)
    else:
        return "Your email has been forwarded to our customer service team for further assistance."

# Streamlit UI
st.title("Email Processor")

# Sample template prompts
sample_emails = [
    "I'm interested in renting a Canon EOS R5 camera. Is it available?",
    "I want to rent an Aputure 120d II lighting kit. What's the price?",
    "Your service was excellent! The equipment was in perfect condition.",
    "I had a terrible experience with the equipment. It was damaged and the customer service was unresponsive.",
    "I'm having trouble with the DJI Ronin-S. How do I calibrate it?",
    "Help, I'm not getting any signal from my Rode NTG3. What should I do?",
]

# Creating a dropdown for sample emails
selected_sample = st.selectbox("Select a sample email or write your own:", ["Enter your email..."] + sample_emails)

if selected_sample == "Write your own":
    email_content = st.text_area("Enter your email content:")
else:
    email_content = selected_sample
    st.text_area("Email content:", value=email_content, height=100, disabled=True)

if st.button("Process Email"):
    if email_content:
        with st.spinner("Processing..."):
            response = process_email(email_content)
        st.success("Email processed successfully!")
        st.write("Response:")
        st.write(response)
    else:
        st.warning("Please enter an email content.")

conn.close()