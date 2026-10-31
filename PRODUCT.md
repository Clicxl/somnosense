# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
React + Tailwind CSS (frontend), Flask (backend). Chosen by the user.

## Users
Not yet specified. The project is an engineering degree mini project; the audience for the dashboard (the student/evaluators demoing it, or end users monitoring their own sleep) is an open decision.

## Product Purpose
A website that connects to multiple sleep sensors, displays their readings, and computes and shows a sleep score.

## Capabilities and Constraints
- Ingest readings from multiple sleep sensors (which sensors, hardware, and transport are undecided).
- Display each sensor's readings on the website.
- Display a derived sleep score (scoring method undecided).
- Flask backend serves/ingests the data; React + Tailwind frontend renders it.
- Open: sensor types, data rate (live vs. recorded sessions), persistence, authentication, and who the viewer is.

## Evidence on Hand
None yet. No sensor data, sample readings, or scoring formula exist in the repo; do not fabricate them.

## Product Principles
- Readings are real data: show what the sensors report, and label simulated or sample data as such.
- The sleep score must be explainable: show which inputs drive it.
- Multiple sensors are first-class: the interface must hold several sources at once without confusion.
