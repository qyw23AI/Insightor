# PR Submission Guidelines

[中文版本](pr-submission-guidelines.zh-CN.md)

## 1. Other Invalid Cases

- The PR description is blank or seriously inconsistent with the actual code changes.

- Third-party libraries or frameworks are used, but the dependencies are not listed in the README, and the original parts of the functionality are not clearly described.

- Code snippets reused from your own previous work are not cited in the PR description.

## 2. PR (Pull Request) Submission Guidelines

### 2.1 Develop Based on a PR

Please add new functionality based on a PR.

### 2.2 Single-Responsibility Principle

Each PR should do only one thing:

- Each PR should implement or modify only one feature;
- Prefer PRs that are as small and fine-grained as possible;
- Large features should be split into multiple independent PRs and submitted step by step.

### 2.3 PR Content Requirements

The PR title and description must be clear and complete, and should include:

#### Title

A one-sentence summary of what this PR adds or changes.

#### Feature Description

Describe the purpose of the feature and how to use it.

#### Implementation Approach

Briefly explain the technology choices or core implementation logic.

#### Testing Method

How to verify that the feature works correctly.

### 2.4 Main Branch Requirement

After the PR is merged, the main branch must remain runnable, and reviewers should be able to reproduce the demo effect at any time.