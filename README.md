<p align="center">
  <img src="img/banner.png" alt="Aisei Banner" width="100%">
</p>

# **Aisei**
This repository contains the source code for Aisei, an AI-powered language learning application designed to streamline vocabulary acquisition through dynamic content generation.

---

## **About**
Traditional Spaced Repetition Systems (SRS), such as Anki, are highly effective but often rely on static, user-created flashcards. These systems present several inherent challenges:

- **Maintenance Overhead:** Creating and managing decks is time-consuming and often becomes a barrier to consistent study.

- **Context Dependency:** Learning a word within a single, fixed sentence can lead to "sentence memorization" rather than genuine vocabulary mastery.

- **Manual Management:** Users must manually prune and update decks to keep them relevant to their current proficiency level.

- **Accessibility:** The complexity of managing these systems can be intimidating for newcomers to language learning.

Aisei addresses these issues by integrating AI-driven content generation on top of the SM-2 open-source SRS scheduler. Instead of reviewing static flashcards, learners receive dynamically generated sentence cards tailored specifically to their current vocabulary level.

---

## **Technical Features**
Aisei automates the content pipeline while preserving the scientifically validated benefits of spaced repetition:

**Dynamic Review Engine**
The application utilizes OpenAI to generate a unique sentence for every review session. This ensures learners encounter vocabulary in diverse contexts, effectively breaking context dependency.

**Integrated Text-to-Speech (TTS)**
Native ElevenLabs TTS integration provides immediate audio for every generated sentence, facilitating listening comprehension alongside reading practice.

**SM-2 Implementation**
The core scheduling logic utilizes the SM-2 algorithm to calculate optimal review intervals and maximize long-term retention.
