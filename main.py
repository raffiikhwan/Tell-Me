# Impor pustaka (library) yang diperlukan
import google.generativeai as genai
import streamlit as st
import requests
import os
from dotenv import load_dotenv
import PyPDF2
import tempfile
import pandas as pd
import json
import json

# Muat variabel lingkungan dari file .env (untuk menyimpan kunci API)
load_dotenv()
telkom_api_key = os.getenv("TELKOM_API_KEY")

st.title("🤖 AI Assistant with Role-Play & Knowledge Base")

# Konfigurasi Gemini API menggunakan kunci yang diambil dari environment
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Daftar peran (role) yang telah ditentukan sebelumnya untuk AI
# Setiap peran memiliki prompt sistem (perintah) dan ikon sendiri
ROLES = {
    "Artificial Account Manager": {
    "system_prompt": "Anda adalah Artificial Account Manager di perusahaan B2B Telekomunikasi.\n\nTugas Anda:\n1. Berpikir dan bertindak seperti Account Manager profesional di industri B2B Telekomunikasi.\n2. Memberikan rekomendasi strategi pendekatan yang realistis dan efektif untuk calon pelanggan.\n3. Belajar dari tren industri terbaru dan hasilkan insight singkat yang sangat membantu untuk Account Manager.\n4. Memiliki orientasi terhadap deal dan selalu berupaya menambah revenue Telkom.\n5. Selalu siap membantu simulasi atau role-play antara Account Manager dan Calon Pelanggan, baik untuk latihan maupun persiapan meeting.\n\nInstruksi tambahan: Jika user meminta rekomendasi, selalu tanyakan usecase spesifik atau kebutuhan utama sebelum memberikan solusi.\n\nJawablah dengan bahasa yang profesional, ringkas, dan mudah dipahami. Jika diminta simulasi, berikan dialog yang relevan.",
        "icon": "💼",
    },
}


# Fungsi untuk mengekstrak teks dari file PDF yang diunggah
def extract_text_from_pdf(pdf_file):
    """Mengekstrak teks dari file PDF yang diunggah"""
    try:
        # Buat file sementara untuk menyimpan PDF yang diunggah
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_file_path = tmp_file.name

        # Buka dan baca file PDF sementara
        with open(tmp_file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            # Loop setiap halaman dalam PDF untuk mengambil teksnya
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

        # Hapus file sementara setelah selesai diproses
        os.unlink(tmp_file_path)
        return text
    except Exception as e:
        # Tampilkan pesan error jika gagal mengekstrak teks
        st.error(f"Error extracting PDF text: {str(e)}")
        return None


# Fungsi untuk mengekstrak teks dari file Excel yang diunggah
def extract_text_from_excel(excel_file, as_dataframe=False):
    try:
        df = pd.read_excel(excel_file, engine="openpyxl")
        if as_dataframe:
            return df
        text = ""
        for index, row in df.iterrows():
            text += " ".join(str(cell) for cell in row) + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting Excel text: {str(e)}")
        return None


# --- Bagian Sidebar untuk Konfigurasi ---
with st.sidebar:
    # Otomatis load knowledge base saat startup
    try:
        with open("knowledge_base.json", "r", encoding="utf-8") as f:
            st.session_state.knowledge_base = json.load(f)
    except Exception:
        if "knowledge_base" not in st.session_state:
            st.session_state.knowledge_base = ""

    # Otomatis load chat history saat startup
    try:
        with open("chat_history.json", "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
    except Exception:
        if "messages" not in st.session_state:
            st.session_state.messages = []
    st.header("⚙️ Configuration")
    st.subheader("🛠️ Engine Selection")
    engine = st.selectbox("Choose Engine:", ["Gemini", "Telkom"], index=0)

    # Pilihan untuk mengubah peran (role) AI
    selected_role = "Artificial Account Manager"

    # Bagian untuk mengunggah file PDF dan Excel sebagai basis pengetahuan (knowledge base)
    st.subheader("📚 Knowledge Base")
    uploaded_files = st.file_uploader(
        "Upload PDF or Excel documents:",
        type=["pdf", "xlsx"],
        accept_multiple_files=True,
    )

    # Proses file yang diunggah
    if uploaded_files:
        if "knowledge_base" not in st.session_state:
            st.session_state.knowledge_base = ""
        new_knowledge = ""
        for uploaded_file in uploaded_files:
            st.write(f"📄 Processing: {uploaded_file.name}")
            file_type = uploaded_file.type
            if file_type == "application/pdf":
                pdf_text = extract_text_from_pdf(uploaded_file)
                if pdf_text:
                    new_knowledge += (
                        f"\n\n=== DOCUMENT: {uploaded_file.name} ===\n{pdf_text}"
                    )
            elif file_type in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ]:
                pass
        if new_knowledge and new_knowledge not in st.session_state.knowledge_base:
            st.session_state.knowledge_base += new_knowledge
            st.success(f"✅ Processed {len(uploaded_files)} document(s)")
            # Otomatis save knowledge base setelah update
            with open("knowledge_base.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.knowledge_base, f, ensure_ascii=False, indent=2)

    # Tombol untuk menghapus seluruh basis pengetahuan
    if st.button("🗑️ Clear Knowledge Base", key="clear_knowledge_base_btn"):
        st.session_state.knowledge_base = ""
        with open("knowledge_base.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.knowledge_base, f, ensure_ascii=False, indent=2)
        st.success("Knowledge base cleared!")

    # Tampilkan status basis pengetahuan (jumlah kata)
    if "knowledge_base" in st.session_state and st.session_state.knowledge_base:
        word_count = len(st.session_state.knowledge_base.split())
        st.metric("Knowledge Base", f"{word_count} words")

    # Save Chat History button (moved below knowledge base status)
    st.subheader("💾 Chat History")
    if st.button("Save Chat History"):
        with open("chat_history.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)
        st.success("Chat history saved to chat_history.json!")

    if st.button("Load Chat History"):
        try:
            with open("chat_history.json", "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
            st.success("Chat history loaded from chat_history.json!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load chat history: {str(e)}")

# --- Inisialisasi Session State ---
# Session state digunakan untuk menyimpan data antar interaksi pengguna

# Inisialisasi model Gemini jika belum ada
if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = "gemini-2.5-flash"

# Inisialisasi riwayat pesan jika belum ada
if "messages" not in st.session_state:
    st.session_state.messages = []

# Inisialisasi peran saat ini jika belum ada
if "current_role" not in st.session_state:
    st.session_state.current_role = selected_role

# Atur ulang percakapan jika pengguna mengganti peran AI
if st.session_state.current_role != selected_role:
    st.session_state.messages = []  # Kosongkan riwayat chat
    st.session_state.current_role = selected_role
    st.rerun()  # Muat ulang aplikasi untuk menerapkan perubahan

# --- Antarmuka Chat Utama ---

# Tampilkan peran yang sedang aktif
st.markdown(f"**Current Role:** {ROLES[selected_role]['icon']} {selected_role}")

# Tampilkan riwayat percakapan dari sesi sebelumnya
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input chat dari pengguna
if prompt := st.chat_input("What can I help you with?"):
    # Tambahkan pesan pengguna ke riwayat chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Otomatis save chat history setelah update
    with open("chat_history.json", "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)
    with st.chat_message("user"):
        st.markdown(prompt)

    # Hasilkan respons dari asisten AI
    with st.chat_message("assistant"):
        if engine == "Telkom":
            st.info("Telkom engine selected. Sending request to Telkom API...")
            # Replace with your actual Telkom API endpoint
            telkom_api_url = "https://api.telkom.com/endpoint"
            headers = {"Authorization": f"Bearer {telkom_api_key}", "Content-Type": "application/json"}
            payload = {"question": prompt}
            try:
                response = requests.post(telkom_api_url, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    response_json = response.json()
                    response_text = response_json.get("answer", "No answer returned.")
                else:
                    response_text = f"Error: {response.status_code} - {response.text}"
            except Exception as e:
                response_text = f"API request failed: {str(e)}"
            st.markdown(response_text)
        else:
            # Gemini engine selected
            model = genai.GenerativeModel(st.session_state["gemini_model"])

            # Bangun prompt sistem dengan instruksi peran
            system_prompt = ROLES[selected_role]["system_prompt"]

            # Tambahkan konteks dari basis pengetahuan jika tersedia
            if "knowledge_base" in st.session_state and st.session_state.knowledge_base:
                system_prompt += f"""

                IMPORTANT: You have access to the following knowledge base from uploaded documents. Use this information to answer questions when relevant:

                {st.session_state.knowledge_base}

                When answering questions, prioritize information from the knowledge base when applicable. If the answer is found in the uploaded documents, mention which document it came from.
                """

            # Konversi riwayat pesan ke format yang sesuai untuk Gemini
            chat_history = []

            # Tambahkan prompt sistem sebagai pesan pertama jika ini awal percakapan
            if not st.session_state.messages[:-1]:
                chat_history.append({"role": "user", "parts": [system_prompt]})
                chat_history.append(
                    {
                        "role": "model",
                        "parts": [
                            "I understand. I'll act according to my role and use the knowledge base when relevant. How can I help you?"
                        ],
                    }
                )

            # Tambahkan riwayat percakapan sebelumnya (semua kecuali pesan terakhir dari pengguna)
            for msg in st.session_state.messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                chat_history.append({"role": role, "parts": [msg["content"]]})

            # Mulai sesi chat dengan riwayat yang sudah ada
            chat = model.start_chat(history=chat_history)

            # Gabungkan prompt sistem dengan pertanyaan pengguna hanya untuk interaksi pertama
            if not st.session_state.messages[:-1]:
                full_prompt = f"{system_prompt}\n\nUser question: {prompt}"
            else:
                full_prompt = prompt

            # Kirim pesan dan dapatkan respons secara streaming
            response = chat.send_message(full_prompt, stream=True)

            # Tampilkan respons secara streaming (efek ketikan)
            response_text = ""
            response_container = st.empty()
            for chunk in response:
                if chunk.text:
                    response_text += chunk.text
                    # Tambahkan kursor berkedip untuk efek visual
                    response_container.markdown(response_text + "▌")

            # Tampilkan respons final tanpa kursor
            response_container.markdown(response_text)

        # Tambahkan respons dari asisten ke riwayat chat untuk ditampilkan di interaksi selanjutnya
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        # Otomatis save chat history setelah update
        with open("chat_history.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

# --- Petunjuk Penggunaan di Bagian Bawah ---
with st.expander("ℹ️ How to use"):
    st.markdown("""
    ### Role-Playing:
    - Select different roles from the sidebar
    - Each role has specific behavior and expertise
    - The conversation resets when you change roles

    ### Knowledge Base:
    - Upload PDF or Excel documents in the sidebar
    - Ask questions about the content in your documents
    - The AI will reference the uploaded documents when answering
    - You can upload multiple PDFs and Excel files

    ### Tips:
    - Be specific in your questions for better answers
    - The AI will mention which document information came from
    - Clear the knowledge base to start fresh
    """)