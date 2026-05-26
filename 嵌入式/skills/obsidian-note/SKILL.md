---
name: obsidian-note
description: Organize learning into structured Obsidian notes. Use when the user wants to take notes on something they're learning — technical concepts, protocols, chips, tools, debugging insights — and save them to the Obsidian vault at D:/蒋瀚/Documents/嵌入式.
---

# Obsidian 学习笔记

Invoke this skill when the user is learning something and wants to organize it into notes saved in their Obsidian vault.

## Vault Path

```
D:\蒋瀚\Documents\嵌入式
```

All notes are created inside this vault. 

## Before Writing

1. **Identify the topic category** — suggest an appropriate folder under the vault root. Common categories for this user: `通信协议/`, `芯片手册/`, `RTOS/`, `硬件设计/`, `调试技巧/`, `ESP-IDF/`, `工具链/`. If no existing folder matches, suggest creating one.
2. **Check for existing related notes** — look in the vault for notes that the new note should link to via `[[wiki-link]]`.
3. **Confirm the file name** — mixed style: technical terms in English (e.g., `SPI-bus.md`), concepts in Chinese (e.g., `中断处理.md`). Ask the user if uncertain.

## Note Template

Every note follows this structure:

```markdown
---
date: YYYY-MM-DD
tags: [tag1, tag2]
aliases: [alternative-name]
---

# Title

## 概述
One-paragraph summary of what this is and why it matters.

## 核心概念
- key concept 1
- key concept 2

## 细节
Detailed explanation, diagrams (ASCII), code snippets, register tables, timing diagrams, etc.

## 参考
- datasheet links, reference docs, source URLs

## 相关笔记
- [[related-note-1]]
- [[related-note-2]]
```

## Rules

- **One concept per note.** Don't cram multiple unrelated topics into one file.
- **Use `[[wiki-links]]`** to connect to existing notes in the vault.
- **Frontmatter is required** — always include `date`, `tags`, and `aliases` (English term for Chinese-titled notes, and vice versa).
- **Keep it concise.** Notes should be reference-able, not textbook chapters. Favor bullet points over paragraphs.
- **Code snippets** use fenced blocks with language: ` ```c `, ` ```python `, etc.
- **Chinese for explanations**, English for code and technical identifiers.
- **Tags** are kebab-case: `#spi-bus`, `#esp32`, `#rtos-task`, `#power-management`.

## Folder Convention

| 话题类型 | 文件夹 |
|---|---|
| 通信协议 (SPI, I2C, UART, CAN...) | `通信协议/` |
| 芯片数据手册/寄存器 | `芯片手册/` |
| FreeRTOS / RTOS 相关 | `RTOS/` |
| ESP-IDF 框架 | `ESP-IDF/` |
| 硬件设计/原理图 | `硬件设计/` |
| 调试/问题排查 | `调试技巧/` |
| 工具链/开发环境 | `工具链/` |
| 架构/设计模式 | `架构设计/` |

When a note fits multiple categories, pick the primary one and use tags + `[[wiki-links]]` for cross-reference.

## File Naming

- **Technical protocol/standard names** → English kebab-case: `SPI-bus.md`, `I2C-protocol.md`, `MQTT.md`
- **Chinese concepts** → Chinese: `中断处理.md`, `内存对齐.md`
- **Chip models** → part number as-is: `PCF85063A.md`, `ESP32-S3.md`
- No spaces in filenames. Use `-` not `_`.

## After Writing

- Confirm the note was saved to the correct folder.
- Suggest 1-2 `[[wiki-links]]` the user might want to add from other notes back to this one (backlinks).
- If the note reveals a gap in the vault (a referenced concept with no note yet), mention it — the user may want to create a stub.

## Integration with User's Rules

This skill follows the user's global CLAUDE.md rules: think before writing, keep it simple, surgical edits (don't touch unrelated notes), and prefer Chinese for explanations.
