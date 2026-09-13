import sys
import sqlite3
import os
import re
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt


class GestionaleMedico(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestionale Pazienti & Esami Medicali")
        self.resize(1300, 750)

        # 1. Inizializza il database SQLite
        self.init_db()

        # 2. Inizializza l'interfaccia grafica
        self.init_ui()

        # 3. Carica tutti i pazienti all'avvio
        self.carica_pazienti()

    def init_db(self):
        """Crea il database aumentando il timeout per prevenire blocchi"""
        self.conn = sqlite3.connect("lista_pz.db", timeout=10)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pazienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codice_fiscale TEXT UNIQUE,
                nome TEXT,
                cognome TEXT,
                patologia TEXT,
                dicom_path TEXT,
                pdf_path TEXT
            )
        """)
        self.conn.commit()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- BARRA DI RICERCA PER CODICE FISCALE ---
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("<b>Cerca Paziente (CF):</b>"))

        self.input_cerca = QLineEdit()
        self.input_cerca.setPlaceholderText("Inserisci Codice Fiscale da cercare...")
        self.input_cerca.textChanged.connect(self.cerca_paziente)
        search_box.addWidget(self.input_cerca)

        self.btn_mostra_tutti = QPushButton("Mostra Tutti")
        self.btn_mostra_tutti.clicked.connect(self.ripristina_ricerca)
        search_box.addWidget(self.btn_mostra_tutti)

        main_layout.addLayout(search_box)
        main_layout.addWidget(QLabel("<hr>"))  # Linea di separazione

        # --- FORM DI INSERIMENTO ---
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("<b>Nuovo Paziente / Dati Anagrafici:</b>"))

        self.input_cf = QLineEdit()
        self.input_cf.setPlaceholderText("Codice Fiscale (es. RSSMRA80A01H501U)")
        self.input_cf.setMaxLength(16)

        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Nome")

        self.input_cognome = QLineEdit()
        self.input_cognome.setPlaceholderText("Cognome")

        self.input_patologia = QLineEdit()
        self.input_patologia.setPlaceholderText("Patologia / Note")

        form_layout.addWidget(self.input_cf)
        form_layout.addWidget(self.input_nome)
        form_layout.addWidget(self.input_cognome)
        form_layout.addWidget(self.input_patologia)

        # Selettore DICOM iniziale
        dicom_layout = QHBoxLayout()
        self.btn_dicom = QPushButton("Seleziona File DICOM")
        self.btn_dicom.clicked.connect(self.seleziona_dicom)
        self.label_dicom = QLabel("Nessun file DICOM selezionato")
        dicom_layout.addWidget(self.btn_dicom)
        dicom_layout.addWidget(self.label_dicom)
        form_layout.addLayout(dicom_layout)

        # Selettore PDF iniziale
        pdf_layout = QHBoxLayout()
        self.btn_pdf = QPushButton("Seleziona Referto PDF")
        self.btn_pdf.clicked.connect(self.seleziona_pdf)
        self.label_pdf = QLabel("Nessun file PDF selezionato")
        pdf_layout.addWidget(self.btn_pdf)
        pdf_layout.addWidget(self.label_pdf)
        form_layout.addLayout(pdf_layout)

        # Pulsante Salva
        self.btn_salva = QPushButton("Salva Paziente")
        self.btn_salva.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px;")
        self.btn_salva.clicked.connect(self.salva_paziente)
        form_layout.addWidget(self.btn_salva)

        main_layout.addLayout(form_layout)

        # --- TABELLA RISULTATI ---
        main_layout.addWidget(QLabel("<br><b>Elenco Pazienti:</b>"))

        self.table_pazienti = QTableWidget()
        self.table_pazienti.setColumnCount(8)
        self.table_pazienti.setHorizontalHeaderLabels([
            "ID", "Codice Fiscale", "Nome", "Cognome", "Patologia", "Esami DICOM", "Referti PDF", "Azione"
        ])

        # --- CONFIGURAZIONE LARGHEZZA COLONNE ---
        header = self.table_pazienti.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID stretto
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Codice Fiscale
        header.setSectionResizeMode(2, QHeaderView.Interactive)      # Nome
        header.setSectionResizeMode(3, QHeaderView.Interactive)      # Cognome
        header.setSectionResizeMode(4, QHeaderView.Interactive)      # Patologia
        header.setSectionResizeMode(5, QHeaderView.Stretch)          # Esami DICOM
        header.setSectionResizeMode(6, QHeaderView.Stretch)          # Referti PDF
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) # Azione

        self.table_pazienti.setColumnWidth(0, 45)

        main_layout.addWidget(self.table_pazienti)

    # --- FUNZIONI VALIDAZIONE ---
    @staticmethod
    def valida_codice_fiscale(cf: str) -> bool:
        """Verifica la correttezza formale dei 16 caratteri del Codice Fiscale italiano"""
        pattern = r"^[A-Z]{6}[0-9]{2}[A-Z]{1}[0-9]{2}[A-Z]{1}[0-9]{3}[A-Z]{1}$"
        return bool(re.match(pattern, cf))

    # --- FUNZIONI SELEZIONE ED APERTURA FILE FORM ---
    def seleziona_dicom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Immagine DICOM", "",
                                              "File DICOM (*.dcm);;Tutti i file (*)")
        if path:
            self.label_dicom.setText(path)

    def seleziona_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Referto PDF", "", "File PDF (*.pdf);;Tutti i file (*)")
        if path:
            self.label_pdf.setText(path)

    def apri_file_esterno(self, file_path: str):
        """Apre il file associato con l'applicazione predefinita del sistema"""
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Attenzione", "Il file selezionato non esiste o il percorso non è valido.")
            return

        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file:\n{str(e)}")

    # --- GESTIONE FILE SINGOLI DA TABELLA ---
    def aggiungi_file_paziente(self, id_paziente: int, colonna: str, tipo_file: str):
        """Accoda un nuovo file senza cancellare quelli caricati in precedenza"""
        filtro = "File DICOM (*.dcm);;Tutti i file (*)" if tipo_file == "DICOM" else "File PDF (*.pdf);;Tutti i file (*)"
        path, _ = QFileDialog.getOpenFileName(self, f"Aggiungi File {tipo_file}", "", filtro)

        if path:
            try:
                self.cursor.execute(f"SELECT {colonna} FROM pazienti WHERE id = ?", (id_paziente,))
                row = self.cursor.fetchone()
                percorsi_attuali = row[0] if row and row[0] else ""

                if percorsi_attuali:
                    nuovi_percorsi = f"{percorsi_attuali};{path}"
                else:
                    nuovi_percorsi = path

                query = f"UPDATE pazienti SET {colonna} = ? WHERE id = ?"
                self.cursor.execute(query, (nuovi_percorsi, id_paziente))
                self.conn.commit()

                QMessageBox.information(self, "Aggiornato", f"Nuovo file {tipo_file} aggiunto con successo!")
                self.carica_pazienti()
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile aggiungere il file:\n{str(e)}")

    def elimina_singolo_file(self, id_paziente: int, colonna: str, file_path: str):
        """Rimuove solo il file selezionato dalla stringa di percorsi salvata nel DB"""
        if not file_path:
            return

        nome_file = os.path.basename(file_path)
        conferma = QMessageBox.question(
            self,
            "Conferma Rimozione File",
            f"Sei sicuro di voler rimuovere l'allegato '{nome_file}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if conferma == QMessageBox.Yes:
            try:
                self.cursor.execute(f"SELECT {colonna} FROM pazienti WHERE id = ?", (id_paziente,))
                row = self.cursor.fetchone()
                if row and row[0]:
                    percorsi = [p for p in row[0].split(";") if p and p != file_path]
                    nuovi_percorsi = ";".join(percorsi)

                    self.cursor.execute(f"UPDATE pazienti SET {colonna} = ? WHERE id = ?", (nuovi_percorsi, id_paziente))
                    self.conn.commit()
                    QMessageBox.information(self, "File Rimosso", f"Il file '{nome_file}' è stato rimosso.")
                    self.carica_pazienti()
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile eliminare il file:\n{str(e)}")

    # --- RICERCA ED ELIMINAZIONE DATABASE ---
    def elimina_paziente(self, id_paziente: int, nome_completo: str):
        """Richiede la conferma e cancella l'intero record dal database"""
        conferma = QMessageBox.question(
            self,
            "Conferma Eliminazione Paziente",
            f"Sei sicuro di voler eliminare il paziente {nome_completo} e tutti i suoi dati?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if conferma == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM pazienti WHERE id = ?", (id_paziente,))
                self.conn.commit()
                QMessageBox.information(self, "Eliminato", "Paziente eliminato con successo.")
                self.carica_pazienti()
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile eliminare il paziente:\n{str(e)}")

    def cerca_paziente(self):
        """Filtra la tabella in base al codice fiscale digitato"""
        testo_ricerca = self.input_cerca.text().strip().upper()

        if not testo_ricerca:
            self.carica_pazienti()
            return

        query = "SELECT * FROM pazienti WHERE codice_fiscale LIKE ?"
        self.cursor.execute(query, (f"%{testo_ricerca}%",))
        pazienti = self.cursor.fetchall()
        self.aggiorna_griglia(pazienti)

    def ripristina_ricerca(self):
        """Pulisce il campo di ricerca e mostra tutti i pazienti"""
        self.input_cerca.clear()
        self.carica_pazienti()

    def carica_pazienti(self):
        """Carica l'intero elenco dal database"""
        self.cursor.execute("SELECT * FROM pazienti")
        pazienti = self.cursor.fetchall()
        self.aggiorna_griglia(pazienti)

    def aggiorna_griglia(self, lista_pazienti):
        """Popola la griglia con elementi a dimensione fissa per mantenere l'interfaccia ordinata"""
        self.table_pazienti.setRowCount(0)
        for row_idx, paziente in enumerate(lista_pazienti):
            self.table_pazienti.insertRow(row_idx)

            paziente_id = paziente[0]
            nome_completo = f"{paziente[2]} {paziente[3]}"

            # Inserisce ID, CF, Nome, Cognome e Patologia
            for col_idx in range(5):
                data = paziente[col_idx]
                self.table_pazienti.setItem(row_idx, col_idx, QTableWidgetItem(str(data if data else "")))

            # --- CELLA DICOM MULTIPLI (Colonna 5) ---
            dicom_widget = QWidget()
            dicom_layout = QHBoxLayout(dicom_widget)
            dicom_layout.setContentsMargins(2, 2, 2, 2)
            dicom_layout.setSpacing(4)

            btn_add_dicom = QPushButton("➕")
            btn_add_dicom.setFixedSize(24, 24)
            btn_add_dicom.setToolTip("<b>Aggiungi file DICOM</b>")
            btn_add_dicom.setStyleSheet("font-weight: bold; padding: 0px;")
            btn_add_dicom.clicked.connect(
                lambda _, p_id=paziente_id: self.aggiungi_file_paziente(p_id, "dicom_path", "DICOM")
            )
            dicom_layout.addWidget(btn_add_dicom)

            dicom_paths = [p for p in (paziente[5] or "").split(";") if p]

            if dicom_paths:
                combo_dicom = QComboBox()
                combo_dicom.setFixedHeight(26)
                for p in dicom_paths:
                    combo_dicom.addItem(os.path.basename(p), p)

                btn_open_dicom = QPushButton("📁 Apri")
                btn_open_dicom.setFixedSize(60, 26)
                btn_open_dicom.clicked.connect(
                    lambda _, cb=combo_dicom: self.apri_file_esterno(cb.currentData())
                )

                btn_del_dicom = QPushButton("🗑️")
                btn_del_dicom.setFixedSize(26, 26)
                btn_del_dicom.setToolTip("<b>Elimina il file DICOM selezionato</b>")
                btn_del_dicom.setStyleSheet("padding: 0px;")
                btn_del_dicom.clicked.connect(
                    lambda _, p_id=paziente_id, cb=combo_dicom: self.elimina_singolo_file(p_id, "dicom_path", cb.currentData())
                )

                dicom_layout.addWidget(combo_dicom)
                dicom_layout.addWidget(btn_open_dicom)
                dicom_layout.addWidget(btn_del_dicom)
            else:
                dicom_layout.addStretch()

            self.table_pazienti.setCellWidget(row_idx, 5, dicom_widget)

            # --- CELLA PDF MULTIPLI (Colonna 6) ---
            pdf_widget = QWidget()
            pdf_layout = QHBoxLayout(pdf_widget)
            pdf_layout.setContentsMargins(2, 2, 2, 2)
            pdf_layout.setSpacing(4)

            btn_add_pdf = QPushButton("➕")
            btn_add_pdf.setFixedSize(24, 24)
            btn_add_pdf.setToolTip("<b>Aggiungi file PDF</b>")
            btn_add_pdf.setStyleSheet("font-weight: bold; padding: 0px;")
            btn_add_pdf.clicked.connect(
                lambda _, p_id=paziente_id: self.aggiungi_file_paziente(p_id, "pdf_path", "PDF")
            )
            pdf_layout.addWidget(btn_add_pdf)

            pdf_paths = [p for p in (paziente[6] or "").split(";") if p]

            if pdf_paths:
                combo_pdf = QComboBox()
                combo_pdf.setFixedHeight(26)
                for p in pdf_paths:
                    combo_pdf.addItem(os.path.basename(p), p)

                btn_open_pdf = QPushButton("📄 Apri")
                btn_open_pdf.setFixedSize(60, 26)
                btn_open_pdf.clicked.connect(
                    lambda _, cb=combo_pdf: self.apri_file_esterno(cb.currentData())
                )

                btn_del_pdf = QPushButton("🗑️")
                btn_del_pdf.setFixedSize(26, 26)
                btn_del_pdf.setToolTip("<b>Elimina il PDF selezionato</b>")
                btn_del_pdf.setStyleSheet("padding: 0px;")
                btn_del_pdf.clicked.connect(
                    lambda _, p_id=paziente_id, cb=combo_pdf: self.elimina_singolo_file(p_id, "pdf_path", cb.currentData())
                )

                pdf_layout.addWidget(combo_pdf)
                pdf_layout.addWidget(btn_open_pdf)
                pdf_layout.addWidget(btn_del_pdf)
            else:
                pdf_layout.addStretch()

            self.table_pazienti.setCellWidget(row_idx, 6, pdf_widget)

            # --- CELLA ELIMINA PAZIENTE (Colonna 7) ---
            btn_elimina = QPushButton("❌ Elimina")
            btn_elimina.setFixedHeight(26)
            btn_elimina.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
            btn_elimina.clicked.connect(
                lambda _, p_id=paziente_id, p_nome=nome_completo: self.elimina_paziente(p_id, p_nome)
            )
            self.table_pazienti.setCellWidget(row_idx, 7, btn_elimina)

    def salva_paziente(self):
        cf = self.input_cf.text().strip().upper()
        nome = self.input_nome.text().strip()
        cognome = self.input_cognome.text().strip()
        patologia = self.input_patologia.text().strip()
        dicom_path = self.label_dicom.text() if self.label_dicom.text() != "Nessun file DICOM selezionato" else ""
        pdf_path = self.label_pdf.text() if self.label_pdf.text() != "Nessun file PDF selezionato" else ""

        if not cf or not nome or not cognome:
            QMessageBox.warning(self, "Attenzione", "Codice Fiscale, Nome e Cognome sono obbligatori!")
            return

        if not self.valida_codice_fiscale(cf):
            QMessageBox.critical(
                self,
                "Codice Fiscale Non Valido",
                "Il Codice Fiscale inserito non rispetta il formato ufficiale (16 caratteri)!"
            )
            return

        try:
            # Se il paziente esiste già, recupera i percorsi esistenti ed accoda i nuovi
            self.cursor.execute("SELECT dicom_path, pdf_path FROM pazienti WHERE codice_fiscale = ?", (cf,))
            row = self.cursor.fetchone()

            if row:
                old_dicom, old_pdf = row[0] or "", row[1] or ""
                if old_dicom and dicom_path:
                    dicom_path = f"{old_dicom};{dicom_path}"
                elif old_dicom:
                    dicom_path = old_dicom

                if old_pdf and pdf_path:
                    pdf_path = f"{old_pdf};{pdf_path}"
                elif old_pdf:
                    pdf_path = old_pdf

            self.cursor.execute("""
                INSERT OR REPLACE INTO pazienti (codice_fiscale, nome, cognome, patologia, dicom_path, pdf_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cf, nome, cognome, patologia, dicom_path, pdf_path))
            self.conn.commit()

            # Reset form
            self.input_cf.clear()
            self.input_nome.clear()
            self.input_cognome.clear()
            self.input_patologia.clear()
            self.label_dicom.setText("Nessun file DICOM selezionato")
            self.label_pdf.setText("Nessun file PDF selezionato")

            QMessageBox.information(self, "Successo", "Paziente salvato con successo!")
            self.carica_pazienti()

        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante il salvataggio:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GestionaleMedico()
    window.show()
    sys.exit(app.exec())