#   WordlistImporter
#   Author: Juveria Banu
#   Version: 1.1
from burp import IBurpExtender, IIntruderPayloadGeneratorFactory, IIntruderPayloadGenerator, ITab, IExtensionStateListener
from javax.swing import JPanel, JButton, JTextField, JLabel, BoxLayout, JOptionPane, JScrollPane, JTextArea, JCheckBox, JFileChooser, BorderFactory, Box
from java.awt import BorderLayout, Dimension, FlowLayout, Cursor, Insets, Color
from java.awt.event import ActionListener, MouseAdapter
from java.net import URL
from java.io import BufferedReader, InputStreamReader, File, FileOutputStream, OutputStreamWriter, FileInputStream
from java.util import ArrayList, HashSet
import os
import threading

class BurpExtender(IBurpExtender, IIntruderPayloadGeneratorFactory, ITab, IExtensionStateListener):
    HIGHLIGHT_COLOR = Color(195, 225, 245)

    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        callbacks.setExtensionName("Wordlist Importer")
        self._default_url = ""
        self._url_history = ArrayList()
        self._url_checkboxes = ArrayList()
        self._url_labels = ArrayList()
        self._entry_panels = []
        self._merged_wordlist = ArrayList()
        self._selected_url = None

        # Initialize any background threads or resources that need cleanup
        self._running = True  # Flag to control background threads if any
        self._active_connections = []  # List to track any active network connections
        self._active_readers = []  # List to track any open file readers
        
        # Register ourselves as an extension state listener for clean unloading
        callbacks.registerExtensionStateListener(self)
        
        # Load previously saved URLs from extension and add them to the URL history set
        saved_urls = callbacks.loadExtensionSetting("url_history")
        if saved_urls:
            for url in saved_urls.split("\n"):
                if url.strip():
                    self._url_history.add(url.strip())

        # Setting the margin for the entire extension
        self._panel = JPanel()
        self._panel.setLayout(BoxLayout(self._panel, BoxLayout.Y_AXIS))
        margin = 20
        self._panel.setBorder(BorderFactory.createEmptyBorder(margin, margin, margin, margin))

        # Creating a panel for the textbox to insert URL/path, and "Choose File" and "Import" buttons
        url_panel = JPanel()
        url_panel.setLayout(BoxLayout(url_panel, BoxLayout.X_AXIS))
        url_panel.add(JLabel("Insert URL/File Path:"))
        url_panel.add(Box.createRigidArea(Dimension(10, 0)))
        self._url_field = JTextField(self._default_url, 25)
        self._url_field.setMaximumSize(Dimension(900, 24))
        self._url_field.setPreferredSize(Dimension(900, 24))
        url_panel.add(self._url_field)
        url_panel.add(Box.createRigidArea(Dimension(10, 0)))
        choose_file_button = JButton("Choose File", actionPerformed=self.choose_file_for_url_field)       
        choose_file_button.setPreferredSize(Dimension(120, 24))
        url_panel.add(choose_file_button)
        self._panel.add(url_panel)
        url_panel.add(Box.createRigidArea(Dimension(10, 0)))
        test_button = JButton("Import", actionPerformed=self.test_url)
        test_button.setPreferredSize(Dimension(80, 24))
        url_panel.add(test_button)
        self._panel.add(url_panel)
        self._panel.add(Box.createVerticalStrut(10)) 
        
        # Create a sub-panel to hold buttons side by side
        buttons_panel = JPanel()
        buttons_panel.setLayout(BoxLayout(buttons_panel, BoxLayout.X_AXIS))  # Horizontal layout for buttons

        # Select All button
        select_all_button = JButton("Select All", actionPerformed=self.select_all_checkboxes)
        select_all_button.setPreferredSize(Dimension(120, 24))
        buttons_panel.add(select_all_button)
        
        # Add space between the buttons
        buttons_panel.add(Box.createRigidArea(Dimension(20, 0)))  # Adjust the space as needed
        
        # Clear History button
        clear_history_button = JButton("Clear History", actionPerformed=self.clear_history)
        clear_history_button.setPreferredSize(Dimension(120, 24))
        buttons_panel.add(clear_history_button)
        self._panel.add(buttons_panel)
        
        # Creating a panel for Wordlist History
        combined_panel = JPanel()
        combined_panel.setLayout(BoxLayout(combined_panel, BoxLayout.X_AXIS))        
        url_history_container = JPanel()
        url_history_container.setLayout(BoxLayout(url_history_container, BoxLayout.Y_AXIS))
        label = JLabel("Wordlist History:")
        label.setAlignmentX(0.0)
        label.setPreferredSize(label.getMinimumSize())
        label_panel = JPanel(FlowLayout(FlowLayout.LEFT, 0, 0))
        label_panel.setBorder(BorderFactory.createEmptyBorder(0, 0, 0, 0))
        label_panel.setMaximumSize(Dimension(10000, label.getPreferredSize().height))
        label_panel.add(label)
        url_history_container.add(label_panel)
        url_history_container.setAlignmentX(0.0)

        # History scroll panel
        self._url_history_panel = JPanel()
        self._url_history_panel.setLayout(BoxLayout(self._url_history_panel, BoxLayout.Y_AXIS))
        url_history_scroll = JScrollPane(self._url_history_panel)
        url_history_scroll.setPreferredSize(Dimension(630, 200))
        url_history_container.add(url_history_scroll)
        combined_panel.add(url_history_container)
        combined_panel.add(Box.createRigidArea(Dimension(20, 0)))
        
        
        # Creating a panel to display a sample of 100 words from the wordlist
        sample_panel = JPanel()
        sample_panel.setLayout(BoxLayout(sample_panel, BoxLayout.Y_AXIS))
        sample_panel.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        sample_panel.add(JLabel("Sample from wordlist:"))
        self._sample_area = JTextArea(15, 30)
        self._sample_area.setEditable(False)
        scroll_pane = JScrollPane(self._sample_area)
        scroll_pane.setPreferredSize(Dimension(20, 200))
        scroll_pane.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        sample_panel.add(scroll_pane)
        combined_panel.add(sample_panel)
        self._panel.add(combined_panel)
        self._panel.add(Box.createVerticalStrut(10))

        # Creating a panel for the status messages
        status_panel = JPanel()
        status_panel.setLayout(BoxLayout(status_panel, BoxLayout.Y_AXIS))
        status_panel.setAlignmentX(JPanel.CENTER_ALIGNMENT)
        status_panel.add(Box.createVerticalStrut(5))

        # Creating the status label
        self._status_label = JLabel("Ready")
        self._status_label.setAlignmentX(JPanel.CENTER_ALIGNMENT)
        status_panel.add(self._status_label)
        status_panel.add(Box.createVerticalStrut(10))
        self._panel.add(status_panel)
        
        # Creating a panel for "Merge Wordlists", "Clear Wordlist", and "Export Wordlist" buttons
        button_panel = JPanel()
        button_panel.setLayout(BoxLayout(button_panel, BoxLayout.X_AXIS))
        merge_button = JButton("Merge Wordlists", actionPerformed=self.merge_selected_wordlists)
        merge_button.setPreferredSize(Dimension(80, 20))
        button_panel.add(merge_button)
        button_panel.add(Box.createRigidArea(Dimension(20, 0)))
        clear_button = JButton("Clear Wordlist", actionPerformed=self.clear_merged_wordlist)
        clear_button.setPreferredSize(Dimension(80, 20))
        button_panel.add(clear_button)
        button_panel.add(Box.createRigidArea(Dimension(20, 0)))
        export_button = JButton("Export Wordlist", actionPerformed=self.export_wordlist)
        export_button.setPreferredSize(Dimension(80, 20))
        button_panel.add(export_button)
        self._panel.add(button_panel)
        self.update_url_history_panel()
        callbacks.registerIntruderPayloadGeneratorFactory(self)
        callbacks.addSuiteTab(self)
        callbacks.printOutput("URL Wordlist Importer loaded")

    # Implementation of IExtensionStateListener.extensionUnloaded()
    def extensionUnloaded(self):
        """Clean up resources when extension is unloaded"""
        self._callbacks.printOutput("WordlistImporter extension is being unloaded, releasing resources...")
        
        # Signal all background operations to stop
        self._running = False
        
        # Clear any wordlists from memory
        if self._merged_wordlist:
            self._callbacks.printOutput("Clearing wordlist from memory...")
            self._merged_wordlist.clear()
        
        # Close any open file readers
        for reader in self._active_readers:
            try:
                self._callbacks.printOutput("Closing file reader...")
                reader.close()
            except Exception as e:
                self._callbacks.printError("Error closing reader: " + str(e))
        
        # Close any active network connections
        for conn in self._active_connections:
            try:
                self._callbacks.printOutput("Closing network connection...")
                conn.disconnect()
            except Exception as e:
                self._callbacks.printError("Error closing connection: " + str(e))
        
        # Clear our lists of tracked resources
        self._active_readers = []
        self._active_connections = []
        
        # Ensure GC can reclaim any large wordlists
        self._url_history = None
        self._merged_wordlist = None
        
        self._callbacks.printOutput("WordlistImporter extension unloaded cleanly")
        
    # Action listener for Select All
    def select_all_checkboxes(self, event):
        all_selected = True
        for checkbox in self._url_checkboxes:
            if not checkbox.isSelected():
                all_selected = False
                break

        if all_selected:
            for checkbox in self._url_checkboxes:
                checkbox.setSelected(False)
            event.getSource().setText("Select All")
        else:
            for checkbox in self._url_checkboxes:
                checkbox.setSelected(True)
            event.getSource().setText("Deselect All")

    # Method for actions when Import button is clicked
    def test_url(self, event):
        self._status_label.setText("Importing...")
        threading.Thread(target=self._test_url_worker).start()

    def _test_url_worker(self):
        url = self._url_field.getText().strip()
        try:
            if url == self._default_url:
                self._status_label.setText("Please enter a valid URL or file path.")
                return

            if url.startswith("http"):
                try:
                    conn = URL(url).openConnection()
                    conn.setConnectTimeout(5000)
                    conn.setReadTimeout(5000)
                    conn.setRequestMethod("GET")
                    
                    if conn.getResponseCode() != 200:
                        self._status_label.setText("Error: URL returned status code " + str(conn.getResponseCode()))
                        return
                except Exception as e:
                    self._status_label.setText("Error connecting to URL: " + str(e))
                    return
            else:
                file_obj = File(url)
                if not file_obj.exists():
                    self._status_label.setText("Error: File does not exist")
                    return
                if not file_obj.isFile():
                    self._status_label.setText("Error: Path is not a file")
                    return
                if not file_obj.canRead():
                    self._status_label.setText("Error: File is not readable")
                    return
                    
            if url and url not in self._url_history:
                self._url_history.insert(0, url)
                self.save_url_history()

            elif url in self._url_history:
                self._url_history.remove(url) 
                self._url_history.insert(0, url)
                self.save_url_history()

            if url.startswith("http"): 
                self._import_from_url(url)
            else:
                self.import_from_file_path(url)

            self.update_url_history_panel()  
            

        except Exception as e:
            self._status_label.setText("Error: " + str(e))
            self._sample_area.setText("")
            JOptionPane.showMessageDialog(self._panel,
                "Error: " + str(e),
                "URL Test", JOptionPane.ERROR_MESSAGE)

    # Method to check URL and display information on the UI
    def _import_from_url(self, url):
         threading.Thread(target=self._import_from_url_worker, args=(url,)).start()

    def _import_from_url_worker(self, url):
        try:
            conn = URL(url).openConnection()
            conn.setRequestMethod("GET")
            
            if conn.getResponseCode() == 200:
                file_size = conn.getContentLength()
                def format_size(bytes):
                    if bytes >= 1024 * 1024:
                        return "%.2f MB" % (bytes / 1024.0 / 1024)
                    elif bytes >= 1024:
                        return "%.2f KB" % (bytes / 1024.0)
                    else:
                        return "%d bytes" % bytes

                readable_size = format_size(file_size)
                
                reader = BufferedReader(InputStreamReader(conn.getInputStream()))
                words = []
                line = reader.readLine()
                while line is not None:
                    line = line.strip()
                    if line:
                        words.append(line)
                    line = reader.readLine()
                reader.close()

                self._status_label.setText("Wordlist imported from the URL. Word count: " + str(len(words)) + ", File size: " + str(readable_size))
                self._sample_area.setText("\n".join(words[:100]))
                self._sample_area.setCaretPosition(0)

        except Exception as e:
            self._status_label.setText("Error: " + str(e))
            self._sample_area.setText("")
            JOptionPane.showMessageDialog(self._panel,
                "Error: " + str(e),
                "Import from URL", JOptionPane.ERROR_MESSAGE)

    # Method to choose a local file            
    def choose_file_for_url_field(self, event):
        file_chooser = JFileChooser()
        file_chooser.setDialogTitle("Select Wordlist File")
        result = file_chooser.showOpenDialog(self._panel)

        if result == JFileChooser.APPROVE_OPTION:
            selected_file = file_chooser.getSelectedFile()
            self._url_field.setText(selected_file.getAbsolutePath())

    # Method to read the wordlist from the selected file 
    def import_from_file_path(self, file_path):
        threading.Thread(target=self._import_from_file_path_worker, args=(file_path,)).start()

    def _import_from_file_path_worker(self, file_path):
        try:
            # It's a file path
            file_obj = File(file_path)
            if file_obj.exists():
                file_size = file_obj.length()
                
                def format_size(bytes):
                    if bytes >= 1024 * 1024:
                        return "%.2f MB" % (bytes / 1024.0 / 1024)
                    elif bytes >= 1024:
                        return "%.2f KB" % (bytes / 1024.0)
                    else:
                        return "%d bytes" % bytes

                readable_size = format_size(file_size)
                
                file_input_stream = FileInputStream(file_path)
                reader = BufferedReader(InputStreamReader(file_input_stream, "UTF-8"))
                words = []
                line = reader.readLine()
                while line is not None:
                    line = line.strip()
                    if line:
                        words.append(line)
                    line = reader.readLine()
                reader.close()

                self._status_label.setText("Wordlist imported from the file. Word count: " + str(len(words)) + ", File size: " + str(readable_size))
                self._sample_area.setText("\n".join(words[:100]))
                self._sample_area.setCaretPosition(0)
        except Exception as e:
            self._status_label.setText("Error: " + str(e))
            self._sample_area.setText("")
            JOptionPane.showMessageDialog(self._panel,
                "Error: " + str(e),
                "Import from File", JOptionPane.ERROR_MESSAGE)

   # Method to clear the history
    def clear_history(self, event):
        ch_result = JOptionPane.showConfirmDialog(
            self._panel,
            "Are you sure you want to clear the entire URL history?",
            "Confirm Clear History",
            JOptionPane.YES_NO_OPTION
        )
        if ch_result == JOptionPane.YES_OPTION:
            self._url_history.clear()
            self._selected_url = None
            self._merged_wordlist.clear()  # Unload wordlist from memory
            self.save_url_history()
            self.update_url_history_panel()
            self._sample_area.setText("")
            self._url_field.setText("")
            self._status_label.setText("Wordlist History Cleared")
            self._callbacks.printOutput("Wordlist unloaded due to history clear.")
            
    # Method to select/deselect all checkboxes
    def toggle_select_all(self, select_all):
        for i in range(self._url_checkboxes.size()):
            self._url_checkboxes.get(i).setSelected(select_all)
            
    # Method to update the Wordlist History panel
    def update_url_history_panel(self):
        self._url_history_panel.removeAll()
        self._url_checkboxes.clear()
        self._url_labels.clear()
        self._entry_panels = []
        
        for url in self._url_history.toArray():
            row_panel = JPanel(BorderLayout())
            row_panel.setMaximumSize(Dimension(2000, 30)) 
            
            if url == self._selected_url:
                row_panel.setOpaque(True)
                row_panel.setBackground(self.HIGHLIGHT_COLOR)
            else:
                row_panel.setOpaque(False)
            
            # Creating a panel to display the Wordlist History
            entry_panel = JPanel()
            entry_panel.setLayout(BoxLayout(entry_panel, BoxLayout.X_AXIS))
            entry_panel.setAlignmentX(JPanel.LEFT_ALIGNMENT)
            if url == self._selected_url:
                entry_panel.setOpaque(True)
                entry_panel.setBackground(self.HIGHLIGHT_COLOR)
            else:
                entry_panel.setOpaque(False)
            self._entry_panels.append(entry_panel)

            # Adding a checkbox to each entry in the Wordlist History
            checkbox = JCheckBox()
            checkbox.setFocusable(False)
            checkbox.setOpaque(url == self._selected_url)
            if url == self._selected_url:
                checkbox.setBackground(self.HIGHLIGHT_COLOR)
            self._url_checkboxes.add(checkbox)
            
            
            # Adding a delete button to each entry in the Wordlist History
            delete_button = JButton("Delete")
            delete_button.setMargin(Insets(0, 2, 0, 2))
            delete_button.setFocusPainted(False)
            delete_button.setBorderPainted(True)
            delete_button.setContentAreaFilled(True)
            fixed_size = Dimension(40, 20)
            delete_button.setPreferredSize(fixed_size)
            delete_button.setMaximumSize(fixed_size)
            delete_button.setMinimumSize(fixed_size)
            delete_button.setToolTipText("Remove this URL")
            delete_button.setFocusPainted(False)
            delete_button.addActionListener(DeleteUrlActionListener(self, url))
            delete_button.setOpaque(url == self._selected_url)
            if url == self._selected_url:
                delete_button.setBackground(self.HIGHLIGHT_COLOR)
            
            # Adding the URL/file path to the Wordlist History once imported
            url_label = JLabel("{}".format(url))
            url_label.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR))
            url_label.addMouseListener(UrlLabelClickListener(self, url))
            self._url_labels.add(url_label) 
            
            url_label.setOpaque(url == self._selected_url)
            if url == self._selected_url:
                url_label.setBackground(self.HIGHLIGHT_COLOR)
            
            entry_panel.add(Box.createRigidArea(Dimension(3, 0)))
            entry_panel.add(delete_button)
            entry_panel.add(Box.createRigidArea(Dimension(3, 0)))
            entry_panel.add(checkbox)
            entry_panel.add(Box.createRigidArea(Dimension(3, 0)))
            entry_panel.add(url_label)
            entry_panel.add(Box.createRigidArea(Dimension(3, 0)))
            
            row_panel.add(entry_panel, BorderLayout.CENTER)
            self._url_history_panel.add(row_panel)

        self._url_history_panel.revalidate()
        self._url_history_panel.repaint()
        
    # Method to perform actions when a URL or file path is selected from the Wordlist History
    def select_url(self, url):
        self._selected_url = url
        self._url_field.setText(url)
        self._status_label.setText("Importing...")
        threading.Thread(target=self._select_url_worker, args=(url,)).start()

    def _select_url_worker(self, url):
        words = []

        # Checks if it's a local file path or URL
        if url.startswith("http"):
            try:
                conn = URL(url).openConnection()
                conn.setRequestMethod("GET")
                if conn.getResponseCode() == 200:
                    file_size = conn.getContentLength()
                    def format_size(bytes):
                        if bytes >= 1024 * 1024:
                            return "%.2f MB" % (bytes / 1024.0 / 1024)
                        elif bytes >= 1024:
                            return "%.2f KB" % (bytes / 1024.0)
                        else:
                            return "%d bytes" % bytes

                    readable_size = format_size(file_size)
                    
                    
                    reader = BufferedReader(InputStreamReader(conn.getInputStream()))
                    line = reader.readLine()
                    while line is not None:
                        line = line.strip()
                        if line:
                            words.append(line)
                        line = reader.readLine()
                    reader.close()

                    self._status_label.setText("Wordlist imported from the selected URL. Word count: " + str(len(words)) + ", File size: " + str(readable_size))
                    self._sample_area.setText("\n".join(words[:100]))
                    self._sample_area.setCaretPosition(0)
                else:
                    self._status_label.setText("Preview failed: HTTP " + str(conn.getResponseCode()))
            except Exception as e:
                self._status_label.setText("Preview error: " + str(e)[:50])
                self._callbacks.printError("URL preview error: " + str(e))
        else:
            try:
                file_obj = File(url)
                if not file_obj.exists():
                    self._status_label.setText("Error: File does not exist: " + url)
                    self._callbacks.printError("File does not exist: " + url)
                    return
                    
                file_size = file_obj.length()  # Get file size    
                def format_size(bytes):
                    if bytes >= 1024 * 1024:
                        return "%.2f MB" % (bytes / 1024.0 / 1024)
                    elif bytes >= 1024:
                        return "%.2f KB" % (bytes / 1024.0)
                    else:
                        return "%d bytes" % bytes

                readable_size = format_size(file_size)
                file_input_stream = FileInputStream(file_obj)
                reader = BufferedReader(InputStreamReader(file_input_stream, "UTF-8"))
                
                line = reader.readLine()
                while line is not None:
                    line = line.strip()
                    if line:
                        words.append(line)
                    line = reader.readLine()
                reader.close()

                self._status_label.setText("Wordlist imported from the selected file path. Word count: " + str(len(words)) + ", File size: " + str(readable_size))
                self._sample_area.setText("\n".join(words[:100]))
                self._sample_area.setCaretPosition(0)
            except Exception as e:
                self._status_label.setText("Error reading file: " + str(e)[:50])
                self._callbacks.printError("File reading error: " + str(e))
        
        # Stores the loaded words in the merged wordlist for the intruder
        self._merged_wordlist.clear()
        for word in words:
            self._merged_wordlist.add(word)
        
        self.update_url_history_panel()
        self._callbacks.printOutput("Selected URL/file: " + url)

    # Creates a new instance a wordlist generator based on the current configuration
    def createNewInstance(self, attack):
        if self._merged_wordlist and self._merged_wordlist.size() > 0:
            return StaticWordlistGenerator(self._merged_wordlist)

        url = self._url_field.getText().strip()
        if not url:
            return StaticWordlistGenerator(ArrayList()) 
        
        # Check if it's a URL or file path
        if url.startswith("http"):
            return URLWordlistGenerator(url, self._callbacks)
        else:
            return FileWordlistGenerator(url, self._callbacks)  

    # Method to save the Wordlist History
    def save_url_history(self):
        urls = "\n".join([url for url in self._url_history.toArray()])
        self._callbacks.saveExtensionSetting("url_history", urls)

    # Method to merge selected wordlists
    def merge_selected_wordlists(self, event):
        self._status_label.setText("Merging...")
        threading.Thread(target=self._merge_selected_wordlists_worker).start()

    def _merge_selected_wordlists_worker(self):
        selected_sources = []
        for i in range(self._url_checkboxes.size()):
            if self._url_checkboxes.get(i).isSelected():
                selected_sources.append(self._url_history.get(i))

        if len(selected_sources) < 2:
            JOptionPane.showMessageDialog(self._panel,
                "Select at least two wordlists to merge.",
                "Error", JOptionPane.ERROR_MESSAGE)
            return
        
        # Deduplicates the wordlist when merging
        unique_words = HashSet()
        for source in selected_sources:
            if source.startswith("http"):
                words = self._fetch_wordlist_from_url(source)
            else:
                words = self._fetch_wordlist_from_file(source)

            for word in words:
                unique_words.add(word)

        self._merged_wordlist.clear()
        sorted_words = sorted(list(unique_words))
        for word in sorted_words:
            self._merged_wordlist.add(word)
        
        # Displays the message with the count of source and unique words after deduplicating and sorting. Also updates the sample list.
        self._sample_area.setText("\n".join(sorted_words[:100]))
        self._sample_area.setCaretPosition(0)
        self._status_label.setText("Merged {} sources into {} unique words.".format(len(selected_sources), len(unique_words)))

    # Method used for exporting a merged wordlist
    def export_wordlist(self, event):
        if self._merged_wordlist.size() == 0:
            JOptionPane.showMessageDialog(self._panel,
                "No wordlist available to export. Please merge some wordlists first.",
                "Error", JOptionPane.ERROR_MESSAGE)
            return
        self.save_wordlist_to_file()

    # Method used to clear a merged wordlist
    def clear_merged_wordlist(self, event):
       cw_result = JOptionPane.showConfirmDialog(
            self._panel,
            "Are you sure you want to clear the wordlist from the memory?",
            "Confirm Clear Wordlist",
            JOptionPane.YES_NO_OPTION
        )
       if cw_result == JOptionPane.YES_OPTION:
            self._merged_wordlist.clear()
            self._sample_area.setText("")
            self._url_field.setText("")
            self._status_label.setText("Wordlist cleared.")
            self._callbacks.printOutput("Wordlist cleared.")
            self._selected_url = None
            self.update_url_history_panel()

    # Method to export a wordlist and save it locally
    def save_wordlist_to_file(self):
        self._status_label.setText("Saving...")
        threading.Thread(target=self._save_wordlist_to_file_worker).start()

    def _save_wordlist_to_file_worker(self):
        try:
            file_chooser = JFileChooser()
            file_chooser.setDialogTitle("Select Save Location")
            file_chooser.setFileSelectionMode(JFileChooser.FILES_ONLY)
            default_file = File("exported_wordlist.txt")
            file_chooser.setSelectedFile(default_file)
            result = file_chooser.showSaveDialog(self._panel)

            if result == JFileChooser.APPROVE_OPTION:
                selected_file = file_chooser.getSelectedFile()
                if not selected_file.getName().endswith(".txt"):
                    selected_file = File(selected_file.getAbsolutePath() + ".txt")

                fos = FileOutputStream(selected_file)
                writer = OutputStreamWriter(fos, "UTF-8")
                for i in range(self._merged_wordlist.size()):
                    writer.write(self._merged_wordlist.get(i) + "\n")
                writer.close()

                self._status_label.setText("Wordlist saved to: " + selected_file.getAbsolutePath())
                self._callbacks.printOutput("Wordlist saved to: " + selected_file.getAbsolutePath())
        except Exception as e:
            self._status_label.setText("Error saving wordlist: " + str(e))
            self._callbacks.printError("Error saving wordlist: " + str(e))
            JOptionPane.showMessageDialog(self._panel,
                "Error saving wordlist: " + str(e),
                "Save Failed", JOptionPane.ERROR_MESSAGE)

    # Method to fetch the wordlist from a URL
    def _fetch_wordlist_from_url(self, url):
        try:
            conn = URL(url).openConnection()
            conn.setRequestMethod("GET")
            if conn.getResponseCode() != 200:
                self._callbacks.printError("Failed to fetch wordlist: HTTP " + str(conn.getResponseCode()))
                return []
            reader = BufferedReader(InputStreamReader(conn.getInputStream()))
            lines = []
            line = reader.readLine()
            while line is not None:
                line = line.strip()
                if line:
                    lines.append(line)
                line = reader.readLine()
            reader.close()
            return lines
        except Exception as e:
            self._callbacks.printError("Error fetching wordlist from URL " + url + ": " + str(e))
            return []

    # Method to fetch the wordlist from a file
    def _fetch_wordlist_from_file(self, file_path):
        try:
            file_obj = File(file_path)
            
            # Check if file exists
            if not file_obj.exists():
                self._callbacks.printError("File does not exist: " + file_path)
                return []
                
            file_input_stream = FileInputStream(file_obj)
            reader = BufferedReader(InputStreamReader(file_input_stream, "UTF-8"))
            
            words = []
            line = reader.readLine()
            while line is not None:
                line = line.strip()
                if line:
                    words.append(line)
                line = reader.readLine()
            
            reader.close()
            return words

        except Exception as e:
            self._callbacks.printError("Error reading file " + file_path + ": " + str(e))
            return []

    # Method to display the name of the generator in Intruder    
    def getGeneratorName(self):
        return "Wordlist Importer"

    
    def createNewInstance(self, attack):
        if self._merged_wordlist and self._merged_wordlist.size() > 0:
            return StaticWordlistGenerator(self._merged_wordlist)
        url = self._url_field.getText().strip() or self._default_url
        return URLWordlistGenerator(url, self._callbacks)

    # Method to name the extension's tab
    def getTabCaption(self):
        return "Wordlist Importer"

    # Method to display the main UI component of the extension
    def getUiComponent(self):
        return self._panel

# Class used when for deleting Wordlist History entry
class DeleteUrlActionListener(ActionListener):
    def __init__(self, extender, url):
        self.extender = extender
        self.url = url
    def actionPerformed(self, event):
        result = JOptionPane.showConfirmDialog(
            self.extender._panel,
            "Are you sure you want to delete this entry from the History?",
            "Confirm Deletion",
            JOptionPane.YES_NO_OPTION
        )
        
        if result == JOptionPane.YES_OPTION:
             # Remove the URL from history
            self.extender._url_history.remove(self.url)
            self.extender.save_url_history()
            self.extender.update_url_history_panel()
            
            if self.url == self.extender._selected_url or self.url == self.extender._url_field.getText():
                self.extender._merged_wordlist.clear()
                self.extender._sample_area.setText("")
                self.extender._url_field.setText("")
                self.extender._selected_url = None
                self.extender._callbacks.printOutput("Wordlist unloaded for deleted URL.")
                self.extender._status_label.setText("Deleted: " + self.url)
            else:
                self.extender._status_label.setText("Deleted: " + self.url)

# Class used to apply the changes when a URL is selected
class UrlLabelClickListener(MouseAdapter):
    def __init__(self, extender, url):
        self.extender = extender
        self.url = url
    
    def mouseClicked(self, event):
        self.extender._selected_url = self.url
        self.extender.select_url(self.url) 
        self.extender.update_url_history_panel()

# Class to import the wordlist to Intruder from a static wordlist. Iterates through the list sequentially and provides each entry as a payload.
class StaticWordlistGenerator(IIntruderPayloadGenerator):
    def __init__(self, wordlist):
        self.wordlist = wordlist
        self.index = 0
    def hasMorePayloads(self):
        return self.index < self.wordlist.size()
    def getNextPayload(self, baseValue):
        if self.index < self.wordlist.size():
            payload = self.wordlist.get(self.index)
            self.index += 1
            return payload
        return None

# Class to import the wordlist from a URL, serving one payload at a time
class URLWordlistGenerator(IIntruderPayloadGenerator):
    def __init__(self, url, callbacks):
        self.url = url
        self.callbacks = callbacks
        self.index = 0
        self.words = self.fetch_words_from_url(url)
    def fetch_words_from_url(self, url):
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url  # or raise an error, or ask the user
            conn = URL(url).openConnection()
            conn.setRequestMethod("GET")
            if conn.getResponseCode() != 200:
                self.callbacks.printError("HTTP error: " + str(conn.getResponseCode()))
                return []
            reader = BufferedReader(InputStreamReader(conn.getInputStream()))
            lines = []
            line = reader.readLine()
            while line is not None:
                line = line.strip()
                if line:
                    lines.append(line)
                line = reader.readLine()
            reader.close()
            return lines
        except Exception as e:
            self.callbacks.printError("Error fetching URL: " + str(e))
            return []
    def hasMorePayloads(self):
        return self.index < len(self.words)
    def getNextPayload(self, baseValue):
        if self.index < len(self.words):
            payload = self.words[self.index]
            self.index += 1
            return payload
        return None
# Class to import wordlist to Intruder from a local file.       
class FileWordlistGenerator(IIntruderPayloadGenerator):
    def __init__(self, file_path, callbacks):
        self.file_path = file_path
        self.callbacks = callbacks
        self.index = 0
        self.words = self.fetch_words_from_file(file_path)
    
    # Method to read the file at the given path
    def fetch_words_from_file(self, file_path):
        try:
            file_obj = File(file_path)
            if not file_obj.exists():
                self.callbacks.printError("File does not exist: " + file_path)
                return []
                
            file_input_stream = FileInputStream(file_obj)
            reader = BufferedReader(InputStreamReader(file_input_stream, "UTF-8"))
            
            lines = []
            line = reader.readLine()
            while line is not None:
                line = line.strip()
                if line:
                    lines.append(line)
                line = reader.readLine()
            reader.close()
            return lines
        except Exception as e:
            self.callbacks.printError("Error reading file: " + str(e))
            return []
            
    # Method to check if there are more payloads left        
    def hasMorePayloads(self):
        return self.index < len(self.words)
        
    # Method to return the next word from the wordlist    
    def getNextPayload(self, baseValue):
        if self.index < len(self.words):
            payload = self.words[self.index]
            self.index += 1
            return payload
        return None
