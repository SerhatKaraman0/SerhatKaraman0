# GitHub GraphQL API Documentation

This directory contains the complete GitHub GraphQL API schema (`schema.docs.graphql`) and documentation for working with GitHub's data through GraphQL queries and mutations.

## Table of Contents

- [Overview](#overview)
- [Schema File](#schema-file)
- [Core Concepts](#core-concepts)
- [Authentication](#authentication)
- [Making Requests](#making-requests)
- [Query Examples](#query-examples)
- [Mutation Examples](#mutation-examples)
- [Common Types](#common-types)
- [Pagination](#pagination)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)
- [Additional Resources](#additional-resources)

---

## Overview

The GitHub GraphQL API v4 provides a powerful and flexible way to interact with GitHub data. Unlike REST APIs, GraphQL allows you to:

- Request exactly the data you need (no over-fetching or under-fetching)
- Get multiple resources in a single request
- Navigate relationships between data efficiently
- Strongly typed schema with auto-documentation

The `schema.docs.graphql` file contains the complete type definitions, queries, mutations, and interfaces available in the GitHub API.

---

## Schema File

**File**: `schema.docs.graphql`

This file contains:
- **Queries**: Read operations to fetch data from GitHub
- **Mutations**: Write operations to create, update, or delete data
- **Types**: Object types like `User`, `Repository`, `Issue`, `PullRequest`, etc.
- **Interfaces**: Common contracts like `Actor`, `Node`, `Assignable`
- **Enums**: Fixed sets of values like `PullRequestState`, `IssueState`
- **Input Types**: Arguments for mutations and complex queries
- **Directives**: Schema annotations like `@preview`, `@possibleTypes`, `@deprecated`

---

## Core Concepts

### Entry Points

The API has two main entry points:

1. **Query** (line ~43798 in schema): Read-only operations
2. **Mutation** (line ~24464 in schema): Write operations

### Node Interface

Most GitHub objects implement the `Node` interface, which provides:
- `id: ID!` - A globally unique identifier

You can fetch any object by its ID using:
```python
query = '''
    query($nodeId: ID!) {
        node(id: $nodeId) {
            ... on User {
                login
                name
            }
        }
    }'''

# Variables
variables = {
    "nodeId": "MDQ6VXNlcjE="
}
```

### Connections & Edges

GitHub uses the **Relay connection pattern** for lists:
- **Connection**: Contains `edges`, `nodes`, and `pageInfo`
- **Edge**: Contains `cursor` and `node`
- **PageInfo**: Contains `hasNextPage`, `hasPreviousPage`, `startCursor`, `endCursor`

Example structure:
```python
query = '''
    query($owner: String!, $name: String!, $limit: Int!) {
        repository(owner: $owner, name: $name) {
            issues(first: $limit) {
                edges {
                    cursor
                    node {
                        title
                        number
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "owner",
    "name": "repo",
    "limit": 10
}
```

---

## Authentication

All requests to the GitHub GraphQL API require authentication.

### Endpoint

```
https://api.github.com/graphql
```

### Headers

```http
POST /graphql HTTP/1.1
Host: api.github.com
Authorization: Bearer YOUR_PERSONAL_ACCESS_TOKEN
Content-Type: application/json
```

### Creating a Personal Access Token

1. Go to **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token**
3. Select the scopes you need (e.g., `repo`, `read:user`, `read:org`)
4. Copy the token and store it securely

---

## Making Requests

### Using cURL

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"query": "{ viewer { login name } }"}' \
     https://api.github.com/graphql
```

### Using Python

```python
import requests

url = "https://api.github.com/graphql"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}

query = '''
    query {
        viewer {
            login
            name
            email
        }
    }'''

response = requests.post(url, json={"query": query}, headers=headers)
print(response.json())
```

### Using JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

const query = `
    query {
        viewer {
            login
            name
            email
        }
    }
`;

fetch('https://api.github.com/graphql', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ query })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## Query Examples

### 1. Get Current User Information

```python
query = '''
    query {
        viewer {
            login
            name
            email
            bio
            avatarUrl
            createdAt
            followers {
                totalCount
            }
            following {
                totalCount
            }
        }
    }'''
```

### 2. Get Repository Information

```python
query = '''
    query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            name
            description
            createdAt
            stargazerCount
            forkCount
            issues(first: 5, states: OPEN) {
                totalCount
                nodes {
                    title
                    number
                    author {
                        login
                    }
                }
            }
            pullRequests(first: 5, states: OPEN) {
                totalCount
                nodes {
                    title
                    number
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "octocat",
    "name": "Hello-World"
}
```

### 3. Search Repositories

```python
query = '''
    query($searchQuery: String!, $limit: Int!) {
        search(query: $searchQuery, type: REPOSITORY, first: $limit) {
            repositoryCount
            edges {
                node {
                    ... on Repository {
                        name
                        owner {
                            login
                        }
                        stargazerCount
                        description
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "searchQuery": "language:python stars:>1000",
    "limit": 10
}
```

### 4. Get User's Repositories

```python
query = '''
    query($login: String!, $limit: Int!) {
        user(login: $login) {
            repositories(first: $limit, orderBy: {field: STARGAZERS, direction: DESC}) {
                nodes {
                    name
                    description
                    stargazerCount
                    forkCount
                    primaryLanguage {
                        name
                        color
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "login": "octocat",
    "limit": 10
}
```

### 5. Get Organization Members

```python
query = '''
    query($login: String!, $limit: Int!) {
        organization(login: $login) {
            name
            description
            membersWithRole(first: $limit) {
                totalCount
                nodes {
                    login
                    name
                    avatarUrl
                }
            }
        }
    }'''

# Variables
variables = {
    "login": "github",
    "limit": 10
}
```

### 6. Get Issue Details with Comments

```python
query = '''
    query($owner: String!, $name: String!, $issueNumber: Int!, $commentLimit: Int!) {
        repository(owner: $owner, name: $name) {
            issue(number: $issueNumber) {
                title
                body
                author {
                    login
                }
                comments(first: $commentLimit) {
                    nodes {
                        body
                        author {
                            login
                        }
                        createdAt
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "facebook",
    "name": "react",
    "issueNumber": 1,
    "commentLimit": 5
}
```

### 7. Get Pull Request Reviews

```python
query = '''
    query($owner: String!, $name: String!, $prNumber: Int!, $reviewLimit: Int!) {
        repository(owner: $owner, name: $name) {
            pullRequest(number: $prNumber) {
                title
                state
                reviews(first: $reviewLimit) {
                    nodes {
                        author {
                            login
                        }
                        state
                        body
                        createdAt
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "rails",
    "name": "rails",
    "prNumber": 42,
    "reviewLimit": 5
}
```

### 8. Get User Contribution Activity

```python
query = '''
    query($login: String!, $start_date: DateTime, $end_date: DateTime) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                totalCommitContributions
                totalIssueContributions
                totalPullRequestContributions
                totalPullRequestReviewContributions
                contributionCalendar {
                    totalContributions
                    weeks {
                        contributionDays {
                            contributionCount
                            date
                        }
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "login": "torvalds",
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-12-31T23:59:59Z"
}
```

---

## Mutation Examples

Mutations modify data on GitHub. They follow the pattern:
- Input type: `<MutationName>Input`
- Return type: `<MutationName>Payload`

### 1. Add Comment to Issue

```python
mutation = '''
    mutation($subjectId: ID!, $body: String!) {
        addComment(input: {
            subjectId: $subjectId
            body: $body
        }) {
            clientMutationId
            commentEdge {
                node {
                    body
                    author {
                        login
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "subjectId": "MDU6SXNzdWUx",
    "body": "This is a comment from GraphQL!"
}
```

### 2. Create an Issue

```python
mutation = '''
    mutation($repositoryId: ID!, $title: String!, $body: String!, $labelIds: [ID!]) {
        createIssue(input: {
            repositoryId: $repositoryId
            title: $title
            body: $body
            labelIds: $labelIds
        }) {
            issue {
                number
                title
                url
            }
        }
    }'''

# Variables
variables = {
    "repositoryId": "MDEwOlJlcG9zaXRvcnkx",
    "title": "Bug: Something is broken",
    "body": "Here's a detailed description of the bug.",
    "labelIds": ["MDU6TGFiZWwx"]
}
```

### 3. Add Star to Repository

```python
mutation = '''
    mutation($starrableId: ID!) {
        addStar(input: {
            starrableId: $starrableId
        }) {
            starrable {
                ... on Repository {
                    name
                    stargazerCount
                }
            }
        }
    }'''

# Variables
variables = {
    "starrableId": "MDEwOlJlcG9zaXRvcnkx"
}
```

### 4. Add Labels to Issue

```python
mutation = '''
    mutation($labelableId: ID!, $labelIds: [ID!]!) {
        addLabelsToLabelable(input: {
            labelableId: $labelableId
            labelIds: $labelIds
        }) {
            labelable {
                ... on Issue {
                    title
                    labels(first: 10) {
                        nodes {
                            name
                            color
                        }
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "labelableId": "MDU6SXNzdWUx",
    "labelIds": ["MDU6TGFiZWwx", "MDU6TGFiZWwy"]
}
```

### 5. Close an Issue

```python
mutation = '''
    mutation($issueId: ID!) {
        closeIssue(input: {
            issueId: $issueId
        }) {
            issue {
                number
                state
                closedAt
            }
        }
    }'''

# Variables
variables = {
    "issueId": "MDU6SXNzdWUx"
}
```

### 6. Create Pull Request

```python
mutation = '''
    mutation($repositoryId: ID!, $baseRefName: String!, $headRefName: String!, $title: String!, $body: String) {
        createPullRequest(input: {
            repositoryId: $repositoryId
            baseRefName: $baseRefName
            headRefName: $headRefName
            title: $title
            body: $body
        }) {
            pullRequest {
                number
                title
                url
            }
        }
    }'''

# Variables
variables = {
    "repositoryId": "MDEwOlJlcG9zaXRvcnkx",
    "baseRefName": "main",
    "headRefName": "feature-branch",
    "title": "Add new feature",
    "body": "This PR adds a new feature."
}
```

### 7. Add Reaction to Issue

```python
mutation = '''
    mutation($subjectId: ID!, $content: ReactionContent!) {
        addReaction(input: {
            subjectId: $subjectId
            content: $content
        }) {
            reaction {
                content
            }
            subject {
                ... on Issue {
                    reactionGroups {
                        content
                        users {
                            totalCount
                        }
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "subjectId": "MDU6SXNzdWUx",
    "content": "THUMBS_UP"
}
```

### 8. Request Pull Request Review

```python
mutation = '''
    mutation($pullRequestId: ID!, $userIds: [ID!]!) {
        requestReviews(input: {
            pullRequestId: $pullRequestId
            userIds: $userIds
        }) {
            pullRequest {
                reviewRequests(first: 10) {
                    nodes {
                        requestedReviewer {
                            ... on User {
                                login
                            }
                        }
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "pullRequestId": "MDExOlB1bGxSZXF1ZXN0MQ==",
    "userIds": ["MDQ6VXNlcjE="]
}
```

---

## Common Types

### User

Represents a GitHub user account.

**Key Fields**:
- `login: String!` - Username
- `name: String` - Display name
- `email: String!` - Email address
- `bio: String` - User biography
- `avatarUrl(size: Int): URI!` - Profile picture
- `repositories` - User's repositories
- `followers` - Users following this user
- `following` - Users this user follows
- `organizations` - Organizations the user belongs to

### Repository

Represents a Git repository.

**Key Fields**:
- `name: String!` - Repository name
- `description: String` - Repository description
- `owner: RepositoryOwner!` - User or Organization
- `stargazerCount: Int!` - Number of stars
- `forkCount: Int!` - Number of forks
- `issues` - Repository issues
- `pullRequests` - Repository pull requests
- `defaultBranchRef` - Default branch (usually `main` or `master`)
- `primaryLanguage` - Main programming language

### Issue

Represents an issue in a repository.

**Key Fields**:
- `number: Int!` - Issue number
- `title: String!` - Issue title
- `body: String!` - Issue description
- `state: IssueState!` - `OPEN` or `CLOSED`
- `author: Actor` - User who created the issue
- `assignees` - Users assigned to the issue
- `labels` - Labels applied to the issue
- `comments` - Comments on the issue

### PullRequest

Represents a pull request in a repository.

**Key Fields**:
- `number: Int!` - PR number
- `title: String!` - PR title
- `body: String!` - PR description
- `state: PullRequestState!` - `OPEN`, `CLOSED`, `MERGED`
- `author: Actor` - User who created the PR
- `reviews` - Reviews on the PR
- `commits` - Commits in the PR
- `changedFiles: Int!` - Number of changed files
- `additions: Int!` - Lines added
- `deletions: Int!` - Lines deleted

### Organization

Represents a GitHub organization.

**Key Fields**:
- `login: String!` - Organization login/username
- `name: String` - Organization display name
- `description: String` - Organization description
- `membersWithRole` - Organization members
- `teams` - Organization teams
- `repositories` - Organization repositories

---

## Pagination

GitHub uses **cursor-based pagination** for list fields.

### Forward Pagination

Fetch the first N items:

```python
query = '''
    query($owner: String!, $name: String!, $limit: Int!) {
        repository(owner: $owner, name: $name) {
            issues(first: $limit) {
                edges {
                    cursor
                    node {
                        title
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "owner",
    "name": "repo",
    "limit": 10
}
```

To get the next page, use the `endCursor` from `pageInfo`:

```python
query = '''
    query($owner: String!, $name: String!, $limit: Int!, $after: String!) {
        repository(owner: $owner, name: $name) {
            issues(first: $limit, after: $after) {
                edges {
                    cursor
                    node {
                        title
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "owner",
    "name": "repo",
    "limit": 10,
    "after": "Y3Vyc29yOnYyOpHOABCD"
}
```

### Backward Pagination

Fetch the last N items:

```python
query = '''
    query($owner: String!, $name: String!, $limit: Int!, $before: String!) {
        repository(owner: $owner, name: $name) {
            issues(last: $limit, before: $before) {
                edges {
                    cursor
                    node {
                        title
                    }
                }
                pageInfo {
                    hasPreviousPage
                    startCursor
                }
            }
        }
    }'''

# Variables
variables = {
    "owner": "owner",
    "name": "repo",
    "limit": 10,
    "before": "Y3Vyc29yOnYyOpHOABCD"
}
```

### Best Practices for Pagination

- Use `first` (forward) or `last` (backward), not both
- Limit `first`/`last` to reasonable values (10-100)
- Always check `hasNextPage`/`hasPreviousPage`
- Store cursors if you need to return to a specific position

---

## Rate Limiting

### Check Your Rate Limit

```python
query = '''
    query {
        rateLimit {
            limit
            remaining
            resetAt
            cost
        }
    }'''
```

**Response**:
```json
{
  "data": {
    "rateLimit": {
      "limit": 5000,
      "remaining": 4999,
      "resetAt": "2025-11-01T12:00:00Z",
      "cost": 1
    }
  }
}
```

### Rate Limit Details

- **Primary Rate Limit**: 5,000 points per hour (authenticated requests)
- Each query has a **cost** based on complexity
- Simple queries cost 1 point
- Complex queries with nested fields cost more
- Use the `dryRun` parameter to check cost without executing:

```graphql
query {
  rateLimit(dryRun: true) {
    cost
  }
}
```

### Tips to Reduce Costs

1. Request only the fields you need
2. Limit pagination (`first` / `last`) to reasonable sizes
3. Avoid deeply nested queries
4. Use fragments to reuse field selections

---

## Best Practices

### 1. Use Fragments for Reusability

```python
query = '''
    fragment repoFields on Repository {
        name
        description
        stargazerCount
        forkCount
        primaryLanguage {
            name
        }
    }

    query($login: String!, $limit: Int!) {
        user(login: $login) {
            repositories(first: $limit) {
                nodes {
                    ...repoFields
                }
            }
        }
    }'''

# Variables
variables = {
    "login": "octocat",
    "limit": 10
}
```

### 2. Use Aliases for Multiple Queries

```python
query = '''
    query($owner1: String!, $name1: String!, $owner2: String!, $name2: String!) {
        repo1: repository(owner: $owner1, name: $name1) {
            stargazerCount
        }
        repo2: repository(owner: $owner2, name: $name2) {
            stargazerCount
        }
    }'''

# Variables
variables = {
    "owner1": "facebook",
    "name1": "react",
    "owner2": "vuejs",
    "name2": "vue"
}
```

### 3. Use Variables for Dynamic Queries

```python
query = '''
    query GetRepo($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            name
            description
        }
    }'''

# Variables
variables = {
    "owner": "facebook",
    "name": "react"
}
```

### 4. Handle Errors Gracefully

GraphQL responses can contain both `data` and `errors`:

```json
{
  "data": {
    "repository": null
  },
  "errors": [
    {
      "type": "NOT_FOUND",
      "path": ["repository"],
      "message": "Could not resolve to a Repository with the name 'unknown-repo'."
    }
  ]
}
```

### 5. Use Inline Fragments for Union/Interface Types

```python
query = '''
    query($searchQuery: String!, $limit: Int!) {
        search(query: $searchQuery, type: ISSUE, first: $limit) {
            edges {
                node {
                    ... on Issue {
                        title
                        number
                    }
                    ... on PullRequest {
                        title
                        number
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "searchQuery": "GraphQL",
    "limit": 5
}
```

### 6. Minimize Nested Queries

Avoid deeply nested queries that fetch large amounts of data:

```python
# ❌ Bad: Too many nested levels
query = '''
    query {
        viewer {
            repositories(first: 100) {
                nodes {
                    issues(first: 100) {
                        nodes {
                            comments(first: 100) {
                                nodes {
                                    # ...
                                }
                            }
                        }
                    }
                }
            }
        }
    }'''

# ✅ Good: Limit pagination and nesting
query = '''
    query($repoLimit: Int!, $issueLimit: Int!) {
        viewer {
            repositories(first: $repoLimit) {
                nodes {
                    name
                    issues(first: $issueLimit) {
                        totalCount
                    }
                }
            }
        }
    }'''

# Variables
variables = {
    "repoLimit": 10,
    "issueLimit": 5
}
```

---

## Additional Resources

### Official Documentation

- **GitHub GraphQL API Docs**: [https://docs.github.com/en/graphql](https://docs.github.com/en/graphql)
- **GraphQL Explorer**: [https://docs.github.com/en/graphql/overview/explorer](https://docs.github.com/en/graphql/overview/explorer) (interactive playground)
- **GitHub GraphQL API Reference**: [https://docs.github.com/en/graphql/reference](https://docs.github.com/en/graphql/reference)

### GraphQL Fundamentals

- **GraphQL Official Site**: [https://graphql.org/](https://graphql.org/)
- **How to GraphQL**: [https://www.howtographql.com/](https://www.howtographql.com/)
- **GraphQL Spec**: [https://spec.graphql.org/](https://spec.graphql.org/)

### Tools & Libraries

- **GraphiQL**: Interactive GraphQL IDE
- **Apollo Client**: GraphQL client for JavaScript/React
- **urql**: Lightweight GraphQL client
- **graphql-request**: Minimal GraphQL client
- **gql**: Python GraphQL client
- **ghapi**: Python GitHub API client

### Schema Introspection

You can query the schema itself to explore types, fields, and documentation:

```python
query = '''
    query {
        __schema {
            types {
                name
                description
            }
        }
    }'''
```

Query a specific type:

```python
query = '''
    query($typeName: String!) {
        __type(name: $typeName) {
            fields {
                name
                type {
                    name
                }
            }
        }
    }'''

# Variables
variables = {
    "typeName": "Repository"
}
```

---

## Quick Reference

### Common Query Patterns

| Task | Query Entry Point |
|------|------------------|
| Get authenticated user | `viewer` |
| Get user by login | `user(login: "username")` |
| Get repository | `repository(owner: "owner", name: "name")` |
| Get organization | `organization(login: "org")` |
| Search repositories/issues/users | `search(query: "...", type: REPOSITORY)` |
| Get node by ID | `node(id: "...")` |

### Common Mutation Patterns

| Task | Mutation |
|------|----------|
| Create issue | `createIssue` |
| Add comment | `addComment` |
| Close issue | `closeIssue` |
| Create PR | `createPullRequest` |
| Add reaction | `addReaction` |
| Add star | `addStar` |
| Add labels | `addLabelsToLabelable` |

### Common Enums

- **IssueState**: `OPEN`, `CLOSED`
- **PullRequestState**: `OPEN`, `CLOSED`, `MERGED`
- **ReactionContent**: `THUMBS_UP`, `THUMBS_DOWN`, `LAUGH`, `HOORAY`, `CONFUSED`, `HEART`, `ROCKET`, `EYES`
- **SearchType**: `ISSUE`, `REPOSITORY`, `USER`, `DISCUSSION`

---

## Example: Complete Workflow

Here's a complete example workflow that creates an issue, adds a comment, and closes it:

```python
import requests

TOKEN = "YOUR_GITHUB_TOKEN"
URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Get repository ID
query_repo = '''
    query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            id
        }
    }'''

variables = {"owner": "owner", "name": "repo"}
response = requests.post(URL, json={"query": query_repo, "variables": variables}, headers=HEADERS)
repo_id = response.json()["data"]["repository"]["id"]

# 2. Create an issue
mutation_create = '''
    mutation($repoId: ID!, $title: String!, $body: String!) {
        createIssue(input: {
            repositoryId: $repoId
            title: $title
            body: $body
        }) {
            issue {
                id
                number
                url
            }
        }
    }'''

variables = {
    "repoId": repo_id,
    "title": "Test Issue from GraphQL",
    "body": "This is a test issue created via the GraphQL API."
}
response = requests.post(URL, json={"query": mutation_create, "variables": variables}, headers=HEADERS)
issue_data = response.json()["data"]["createIssue"]["issue"]
issue_id = issue_data["id"]
print(f"Created issue #{issue_data['number']}: {issue_data['url']}")

# 3. Add a comment
mutation_comment = '''
    mutation($issueId: ID!, $body: String!) {
        addComment(input: {
            subjectId: $issueId
            body: $body
        }) {
            commentEdge {
                node {
                    id
                    body
                }
            }
        }
    }'''

variables = {
    "issueId": issue_id,
    "body": "This is a comment added via GraphQL!"
}
response = requests.post(URL, json={"query": mutation_comment, "variables": variables}, headers=HEADERS)
print("Comment added!")

# 4. Close the issue
mutation_close = '''
    mutation($issueId: ID!) {
        closeIssue(input: {
            issueId: $issueId
        }) {
            issue {
                number
                state
            }
        }
    }'''

variables = {"issueId": issue_id}
response = requests.post(URL, json={"query": mutation_close, "variables": variables}, headers=HEADERS)
print("Issue closed!")
```

---

## Summary

This README provides a comprehensive guide to working with the GitHub GraphQL API using the `schema.docs.graphql` file as reference. Key takeaways:

- Use **queries** for read operations, **mutations** for writes
- Leverage **pagination** with cursors for large datasets
- Monitor **rate limits** to avoid throttling
- Use **fragments** and **variables** for cleaner, reusable queries
- Always handle **errors** gracefully
- Explore the schema with **introspection queries**

For more detailed information on specific types, fields, or operations, refer to the `schema.docs.graphql` file or the official GitHub GraphQL API documentation.

Happy querying! 🚀
