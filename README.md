<p align="center">
  <img src="img/banner.png" alt="Aisei Banner" style="max-width: 100%; height: auto;">
</p>

# **Aisei**

Aisei is an AI-assisted spaced repetition language learning app designed to make vocabulary study more dynamic, approachable, effective, and efficient.

Traditional Spaced Repetition Systems (SRS), such as Anki, are powerful tools for long-term vocabulary retention, but they often depend on static user-created cards that can be intimidating to manage. Aisei keeps the core SRS review loop while adding AI-generated example sentences and translations, ElevenLabs text-to-speech audio, simplified and AI-assisted manual vocab input, automatic card regeneration to reduce context dependency, and progress tracking.

The current MVP serves as a proof of concept with a limited scope of beginner-level Spanish vocabulary. The long-term idea is to use this architecture as the foundation for a fuller language-learning system that supports learners from their first vocabulary cards all the way to advanced native-level study. The app leverages AI to make spaced repetition more approachable for beginners, make study workflows faster and easier to maintain for advanced learners, and improve learning effectiveness across all levels.

---

## **About**

Spaced repetition works by scheduling reviews around when a learner is likely to forget, making it a powerful tool for memorization and long-term retention. However, traditional flashcard workflows typically have several functional problems:

- **Manual card creation:** Users often have to provide their own sentences, translations, and audio resources, which adds time and complexity to study sessions.
- **Static context:** Seeing the same sentence repeatedly can lead to memorizing the card itself instead of learning the vocabulary in more transferable contexts.
- **Beginner friction:** New learners may find SRS setup, deck management, and card creation intimidating. There is a "learning how to learn" barrier to entry.
- **Limited deck flexibility:** Prebuilt decks can help users get started, but they are still limited by what someone else has already created, are finite, and may not match the learner’s goals, ability level, or interests.
- **Card management friction:** Adding new cards or editing existing ones can be intimidating when users have to manage card fields, formatting, sentences, translations, and audio manually.

Aisei addresses these issues by combining spaced repetition with AI-assisted card creation, automatic context refreshing, and integrated audio. The app can create useful review cards from minimal user input, refresh example sentences over time, and preserve each user's learning history separately from the generated content shown on a card.

---

## **Project Goals**

The main goal of Aisei is to make spaced repetition more approachable, more dynamic, and less dependent on manually created flashcard decks.

Aisei is designed around a few core ideas:

- **Automatic context refreshing:** Instead of forcing learners to review the same static sentence forever, Aisei automatically regenerates card content after specific review milestones so vocabulary appears in new contexts over time. This helps reduce a learner’s dependence on a single example sentence when understanding a vocab item, supporting deeper and more transferable vocabulary knowledge.

- **Simplified sentence mining:** A learner should be able to create a useful study card from only a target-language term. Aisei can fill in the missing pieces, including the English meaning, example sentence, translation, and audio.

- **Beginner-friendly workflow:** Traditional SRS tools can be intimidating because users often have to understand deck management, card formatting, sentence mining, and review settings before they can study effectively. Aisei aims to provide a simpler default workflow that can take a learner from beginner-level study toward advanced review without requiring them to manually build the entire system themselves.

- **Useful for advanced learners:** Aisei is not only intended for beginners. Advanced learners can use the same pipeline to simplify sentence mining, refresh stale cards, add vocabulary quickly, and reduce the time spent maintaining decks. The goal is to improve learning efficiency without removing the benefits of active review.

- **Expandable central learning path:** Instead of relying only on manually imported decks, Aisei can function around a central default workflow that grows with the learner. Seeded vocabulary provides structure, while simple manual input makes the system expandable indefinitely.

- **Listening and shadowing support:** Integrated audio gives learners a way to hear vocabulary and example sentences, supporting listening comprehension, pronunciation practice, and shadowing.

---

## **Long-Term Vision**

Aisei’s architecture is built around a reusable pipeline: vocabulary input, generated card content, spaced repetition scheduling, audio generation, review history, and progress tracking. Over time, that same pipeline could support much broader language-learning workflows.

Possible long-term directions include (but are not limited to):

- **Custom learning paths:** AI could be leveraged to easily reorganize default vocabulary paths around a learner’s goals. For example, one user might prioritize business language, while another might prioritize travel, school, conversation, media comprehension, or technical vocabulary.

- **Multiple target languages:** The same core pipeline could be adapted beyond Spanish. Since the app separates scheduling, generated content, audio, and vocabulary data, the architecture could support many target languages with straightforward expansion.

- **Native-language flexibility:** The app could eventually support learners from different native-language backgrounds. Instead of assuming English translations and explanations, the generation layer could produce meanings, translations, and guidance in the learner’s preferred native language.

- **Learner-targeted immersion content:** As the app collects more review history, it could understand which words a learner has already studied. That knowledge could eventually be used to generate custom immersion content, such as short readings, dialogues, listening exercises, or AI-generated podcasts targeted to the learner’s current vocabulary level.

- **More personalized review experiences:** The system could use review performance, known vocabulary, and user preferences to adjust generated sentence difficulty, content domains, and audio practice over time.

---

## **Current MVP Features**

### **SM-2 Review Scheduling**

Aisei uses an open-source SM-2 based scheduler to calculate review intervals and due dates. Each user has independent progress for every vocabulary item, allowing the app to track whether a card is new, learning, relearning, or in long-term review. The review page includes the familiar Again, Hard, Good, and Easy rating flow, with preview labels that show the next interval for each choice.

### **AI-Generated Card Content**

Aisei uses OpenAI's GPT API to generate Spanish example sentences and English translations for vocabulary items. Generated content is saved separately from the user's scheduling progress, so the app can change the sentence shown on a card without resetting the learner's history for that vocab item. This supports the broader goal of reducing static context dependency while preserving the benefits of normal spaced repetition.

### **Text-to-Speech Audio**

Aisei integrates ElevenLabs text-to-speech for vocabulary words and example sentences. Audio can be generated from the review page by clicking on either the vocab term or on the Spanish sentence, and users can choose from supported voices and adjust playback speed. Generated audio is tied to the selected voice and text, allowing repeated playback to reuse existing generated files.

### **Card Regeneration**

Cards are marked for regeneration after specific review milestones. Currently, this milestone is reached when a card meets both a minimum review interval and a minimum success streak. When regeneration occurs, Aisei creates a new generated card version and makes it the active version for review, while the old version is stored in the database. This allows vocabulary to appear in new sentence contexts over time while keeping the same underlying review state, interval, and due-date history.

### **Manual Vocab Input**

Users can add their own vocabulary directly from the review page. Only the target-language term is required. The English meaning, example sentence, and sentence translation are optional and can be completed through the generation pipeline. This keeps manual sentence mining lightweight while still allowing users to provide their own content when they want more control.

### **Stats and Progress Tracking**

The stats page includes daily review totals, rating distribution, future due cards, card type breakdown, retention data, and long-term progress metrics. This gives users both a short-term view of the current study day and a broader view of their learning progress over time.

### **Simulated Time Controls**

The app includes simulated time controls for testing spaced repetition behavior without waiting real days between reviews. This is mainly useful for development, demos, and verifying that due dates, learning steps, and future review counts behave as expected.

---

## **Project Structure**

```text
app/              Main Flask application package
  blueprints/     Route definitions and page-specific templates for auth, review, settings, and stats
  clients/        OpenAI and ElevenLabs API wrappers
  models/         SQLModel database models
  services/       Review, queue, generation, stats, auth, scheduler, and settings logic
  static/         CSS, JavaScript, generated audio, and frontend assets
  templates/      Shared Jinja templates
data/             Local SQLite database
img/              README and project images
scripts/          Database setup and seeding scripts
tests/            Test files
app.py            Flask application entrypoint
requirements.txt  Python dependencies
```

The application is organized around a service-layer architecture. Blueprints handle HTTP requests, services contain business logic, models define database tables, and clients act as thin wrappers around external APIs.

---

## **Running the App**

### **Prerequisites**

Install Python 3.11 or newer.

The launcher scripts automatically check and install dependencies from `requirements.txt`.

### **Running Modes**

This project includes two main running modes:

- **Standard mode:** Preserves the existing local database across runs.
- **Demo mode:** Deletes and re-seeds the local database every time, giving a clean starting state.

Use standard mode to preserve the current database. Use demo mode when starting the app for the first time, or when a clean slate is required.

---

### **Windows**

Open the project folder and run:

```bat
run.bat
```

This starts the app normally and preserves the existing database.

To start with a clean demo database instead, run:

```bat
run_demo.bat
```

The app should automatically open in your browser at:

```text
http://127.0.0.1:5000
```

If the browser does not open automatically, copy and paste the address above into your browser.

---

### **Linux / macOS**

Open a terminal in the project folder.

If needed, make the shell scripts executable:

```bash
chmod +x run.sh run_demo.sh
```

Run the standard version:

```bash
./run.sh
```

This starts the app normally and preserves the existing database.

To start with a clean demo database instead, run:

```bash
./run_demo.sh
```

The app should automatically open in your browser at:

```text
http://127.0.0.1:5000
```

If the browser does not open automatically, copy and paste the address above into your browser.

---

### **Stopping the App**

Press `Ctrl+C` in the terminal.

---

## **API Keys**

Aisei can store API keys locally through the app UI after login.

Supported keys:

- OpenAI API key for generated sentences and translations
- ElevenLabs API key for generated audio

Keys are stored locally using Python `keyring`.

The app can still be explored without API keys, but generated content and audio features require valid keys.