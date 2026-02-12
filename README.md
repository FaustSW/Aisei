# AI-Enhanced Spaced Repetition Language Learning App

An AI-powered language learning web application that combines a proven spaced repetition system (SM-2, used by Anki) with dynamic, context-rich sentence generation using large language models.

---

## 📌 Overview

Traditional spaced repetition systems (SRS), such as Anki, are highly effective but often rely on static, user-created flashcards. These can:

- Be time-consuming to build and maintain  
- Encourage context dependency (learning a word only in one fixed sentence)  
- Require significant manual deck management  
- Be intimidating for beginners  

This project addresses those issues by integrating AI-driven content generation on top of an open-source SRS scheduler. Instead of reviewing static flashcards, learners receive dynamically generated sentence cards tailored to their current vocabulary level.

---

## 🎯 Problem Statement

Many language learners quit because:

- Building and managing decks is tedious  
- Static flashcards lack meaningful, varied context  
- Vocabulary learned in one sentence does not transfer well  
- There is limited listening comprehension integration  

We aim to reduce friction, improve contextual understanding, and automate content creation while preserving the scientifically validated benefits of spaced repetition.

---

## 🚀 Solution

Our application:

1. Uses an open-source implementation of the **Anki SM-2 spaced repetition algorithm**
2. Integrates an **LLM (via OpenAI API)** to generate contextual sentence-based flashcards
3. Constrains generated content to:
   - Vocabulary the learner has already unlocked
   - At most one new concept per card
4. Regenerates sentences during future reviews to prevent context dependency
5. Integrates **text-to-speech (TTS)** for listening comprehension

Instead of reviewing the same sentence repeatedly, learners encounter vocabulary in new, controlled contexts.
