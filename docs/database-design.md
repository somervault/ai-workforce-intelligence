# Database Design

## Overview

The AI Workforce Intelligence Platform is built using a normalized relational database design to support enterprise-scale workforce management, AI-driven analytics, and seamless third-party integrations.

The database is designed with the following goals:

- Normalized schema (3NF)
- UUID-based primary keys
- Scalability
- High performance
- Easy ServiceNow synchronization
- AI-ready architecture
- Auditability
- Extensible integration model

---

# Database Design Principles

## 1. UUID Primary Keys

All tables use UUID as their primary key instead of auto-increment integers.

Benefits:

- Globally unique
- Easier synchronization across systems
- More secure APIs
- Better suited for distributed architectures

---

## 2. Audit Fields

Every business table should contain:

- created_at
- updated_at
- created_by
- updated_by

These fields allow complete auditing of records.

---

## 3. Soft Deletes

Instead of permanently deleting records, business entities should support soft deletion.

Fields:

- is_deleted
- deleted_at

This preserves historical data and prevents accidental data loss.

---

## 4. Normalization

The database follows Third Normal Form (3NF).

Goals:

- Eliminate duplicate data
- Improve consistency
- Reduce storage
- Simplify maintenance

---

## 5. AI Separation

AI-generated insights are stored separately from business data.

Employee records should never directly contain:

- Burnout Score
- Promotion Score
- AI Summary

Instead, these belong to dedicated AI tables.

---

# Database Domains

The system is divided into the following domains.

## Organization

Responsible for organizational hierarchy.

Entities:

- Department

---

## Employee Management

Responsible for employee information.

Entities:

- Employee

---

## Skills & Certifications

Responsible for employee capabilities.

Entities:

- Skill
- EmployeeSkill
- Certification
- EmployeeCertification

---

## Project Management

Responsible for projects and assignments.

Entities:

- Project
- ProjectMember
- Task

---

## AI Intelligence

Responsible for AI-generated insights.

Entities:

- AIAnalysis
- Recommendation
- TeamRecommendation
- TeamRecommendationMember

---

## Integrations

Responsible for external platform synchronization.

Entities:

- GitHubProfile
- JiraProfile
- CalendarSummary
- SlackProfile

---

## Future Expansion

The schema is intentionally designed for future integrations including:

- Microsoft Graph
- Azure AD
- SAP SuccessFactors
- Workday
- Microsoft Teams
- Confluence
