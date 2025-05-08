<h1>Wordlist Importer</h1>

 A Burp extension, written in Python, which allows seamless importing of wordlists hosted on the Internet directly into Burp Suite.

<h2>Installation</h2>
<ol>
  <li>Download Burp Suite.</li>
  <li>Download the Jython standalone JAR file.</li>
  <li>
    Configure Jython environment in Burp Suite:
    <ol>
      <li>Open Burp Suite.</li>
      <li>Navigate to <strong>Extensions Settings</strong> tab under <strong>Extensions</strong> tab.</li>
      <li>Use the <strong>Python Environment</strong> setting to select the downloaded Jython standalone JAR.</li>
    </ol>
  </li>
  <li>
    Add the Python extension to Burp Suite:
    <ol>
      <li>Open the <strong>Installed</strong> tab under <strong>Extensions</strong> tab.</li>
      <li>Select <strong>Add</strong>.</li>
      <li>Choose <strong>Python</strong> as Extension Type.</li>
      <li>Select the extension's Python file.</li>
      <li>Select <strong>Next</strong>.</li>
      <li>Use the <strong>Wordlist Importer</strong> tab added to Burp Suite.</li>
    </ol>
  </li>
</ol>

<h2>User Guide</h2>

<h3>Importing a Wordlist from a URL</h3>
<ol>
  <li>Input the URL of a raw text file containing the wordlist.</li>
  <li>Select <strong>Import</strong>. The wordlist will then be loaded, and a sample of 100 words will be displayed.</li>
  <li>The URL will then be added to the Wordlist History.</li>
</ol>

<h3>Importing a Wordlist from a Local File</h3>
<ol>
  <li>Input the path of a local file, or use the <strong>Choose File</strong> option to select one.</li>
  <li>Select <strong>Import</strong>. The wordlist will then be loaded, and a sample of 100 words will be displayed.</li>
  <li>The file path will then be added to the Wordlist History.</li>
</ol>

<h3>Using the Imported Wordlist in Intruder</h3>
<ol>
  <li>Select the Payload type as <strong>Extension-generated</strong> in Intruder.</li>
  <li>Use the <strong>Select generator</strong> option to select the <strong>Wordlist Importer</strong> extension.</li>
  <li>Use <strong>Start Attack</strong> option to use the wordlist imported from the extension.</li>
</ol>

<h3>Merging Wordlists</h3>
<ol>
  <li>Select two or more URLs and/or file paths by ticking their checkboxes.</li>
  <li>Use the <strong>Merge Wordlists</strong> option to merge the wordlists and deduplicate.</li>
  <li>Export the merged wordlists if you would like to store a local copy.</li>
</ol>

<h3>Additional Features</h3>
<ul>
  <li>Clear the wordlist loaded in memory using the <strong>Clear Wordlist</strong> option.</li>
  <li>Clear the Wordlist History using the <strong>Clear History</strong> option.</li>
  <li>Delete a specific wordlist from the history using the <strong>Delete</strong> option.</li>
</ul>


<h2>Disclaimer</h2>
<p>This is an open-source project designed to assist cybersecurity professionals in conducting authorised security assessments. This software is intended for legitimate use only, such as authorised penetration testing and/or non-profit educational purposes. It should only be used on systems or networks that you own or have explicit written permission from the owner of these systems or networks to perform testing.</p>

<p>Misuse of this software for illegal activities, including unauthorised network intrusion, hacking, or any activity that violates applicable laws, is strictly prohibited. Wilbourne, contributors, and any affiliated party assume no responsibility or liability for any damage, misuse, or legal consequences arising from the use of this software. By using our project, you agree to indemnify and hold harmless the project contributors from any claims or legal action.</p>

<p>It is the user's sole responsibility to ensure compliance with all applicable local, state, national, and international laws. Use this software at your own risk.</p>
