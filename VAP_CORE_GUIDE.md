# Understanding WraithSpec VAP Core: A Complete Guide

**What This Guide Covers:** This document explains the WraithSpec VAP Core protocol from first principles, helping you understand not just how to use it but why it exists and how it solves real problems in working with large language models. Whether you're a developer looking to integrate VAP Core into your applications, a researcher interested in the protocol design, or simply curious about better ways to communicate with AI systems, this guide will walk you through everything you need to know.

---

## The Problem: Why VAP Core Exists

Let me start by explaining the problem that motivated this entire project, because understanding the constraints helps you appreciate why the solution is designed the way it is.

When you work with large language models through commercial interfaces like Claude, ChatGPT, or Gemini, you've probably noticed that these systems let you set persistent instructions that apply to all your conversations. In Claude, this is called "Custom Instructions." In ChatGPT, it's the "Custom Instructions" field in settings. These persistent instructions are incredibly powerful because they let you define how the AI should behave across all your interactions without having to repeat yourself in every conversation.

However, there's a catch that becomes apparent once you start trying to do anything sophisticated with these persistent instruction fields. Most commercial interfaces limit these fields to somewhere between one thousand and two thousand characters. That might sound like a lot until you try to encode something complex like a detailed reasoning framework, specific output formatting requirements, verification procedures, safety interlocks, and behavioral preferences all in one place. Suddenly that character limit feels impossibly restrictive.

To give you a concrete example, the original configuration that inspired VAP Core was a behavioral specification for an AI agent that included header policies with unique identifiers and timestamps, behavioral flags controlling things like precision and factuality requirements, reasoning layer controls specifying how deep the agent should think through problems, operational context about which tools were available, and safety interlocks preventing certain types of outputs. When written out in a human-readable format like YAML, this configuration consumed approximately four thousand characters. There was simply no way to fit it into the persistent instruction fields without either drastically simplifying the behavior or finding a way to compress the information.

The naive solution would be to just abbreviate things or remove whitespace. You could turn "MicroTrace with depth equals three" into "MT d=3" and save some characters. The problem with ad-hoc abbreviation is that it becomes unreadable and error-prone. If you abbreviate things differently each time or forget what your abbreviations mean, you end up with a maintenance nightmare. What you need is a systematic compression approach that produces the same output every time for the same input and can be reliably decoded back to its original meaning.

This is where VAP Core comes in. It provides a formal protocol for compressing complex behavioral configurations and task instructions into compact micro-formats that fit comfortably within typical character limits while remaining completely reversible. If you encode something with VAP Core and then decode it, you get back exactly what you started with, character for character. This deterministic behavior is crucial for reliability and auditability.

---

## Core Concepts: Understanding the Building Blocks

VAP Core is built around three main concepts that work together to provide compression, traceability, and coordination across multiple AI agents or sessions. Let me explain each one and how they fit together.

### The Sentinel Block: Session Identity and Provenance

The Sentinel Block is a metadata header that appears at the beginning of VAP Core artifacts. Think of it as a birth certificate for a session that records who created it, when it was created, why it was created, and what resources were involved. The Sentinel Block serves several purposes that become important as your use of AI systems becomes more sophisticated.

First and most obviously, the Sentinel Block marks boundaries between different sessions or contexts. When you're working with AI systems extensively, you might have dozens of ongoing conversations or tasks, and it becomes important to know which artifacts belong together. The Sentinel Block provides a clear visual and semantic marker that says "this is the beginning of a new unit of work."

Second, the Sentinel Block provides a unique session identifier that links related artifacts together. This identifier is called the SID, which stands for Sentinel Identifier. The SID is derived from a cryptographic hash of the session details, which means that two sessions with identical parameters will produce the same SID while two sessions with even slightly different parameters will produce completely different SIDs. This property lets you verify that artifacts claiming to belong to the same session actually do belong together.

Third, the Sentinel Block records provenance information that lets you trace where artifacts came from. The block includes a universally unique identifier for the specific session, the profile or agent name that created it, a UTC timestamp showing exactly when it was created, the intent describing what the session is trying to accomplish, and counts of how many tools and sources are available. This metadata becomes invaluable when you're debugging problems or auditing what happened during a complex multi-agent workflow.

Here's what a Sentinel Block looks like in practice:

```
SENTINEL:7E96:(550e8400-e29b-41d4-a716-446655440000|Violator-Actual|2025-11-05T15:39Z|i:[encode_context]|2i:[trace_audit]|Tools:10|Sources:6)
```

Let me break down each component so you understand what information is encoded here. The format starts with the literal word SENTINEL to make it immediately recognizable. After that comes the SID, which in this example is 7E96. This is a sixteen-bit prefix extracted from the full BLAKE3 hash of the session parameters. Sixteen bits gives you sixty-five thousand possible values, which is enough to make collisions extremely rare (about a one in sixty-five thousand chance per session) while keeping the identifier short.

Following the SID is a colon and then a parenthetical section containing the detailed session metadata. The first field is the full UUID that uniquely identifies this specific session instance. UUIDs are standardized identifiers that have an astronomically low probability of collision, so you can be confident that this identifier will never be reused accidentally.

Next comes the profile name, which in this case is Violator-Actual. This identifies which agent or user created the session. The profile name is important for multi-agent systems where different agents might have different capabilities or permissions, and you need to track which agent was responsible for which outputs.

The timestamp comes next, formatted in ISO 8601 standard: 2025-11-05T15:39Z. The Z at the end indicates UTC timezone, which is crucial for coordination across systems that might be running in different geographic locations. Always using UTC prevents confusion about whether timestamps need timezone adjustment.

The intent field marked with "i:" describes the high-level purpose of this session. In this example, the intent is "encode_context," which tells you that this session is about encoding some contextual information rather than, say, analyzing data or generating creative content. The secondary intent marked with "2i:" provides additional detail, indicating that this encoding task specifically involves trace auditing capabilities.

Finally, the Sentinel Block records resource counts. This example shows Tools:10 and Sources:6, meaning that the session has access to ten different tools and six data sources. These counts are useful for verifying that the execution environment matches expectations and for debugging situations where an agent doesn't have access to something it needs.

### CI1: Configuration Instructions for Persistent Behavior

CI1 is the first of the two micro-format types in VAP Core, and it stands for Configuration Instruction version one. The purpose of CI1 is to encode persistent behavioral settings that should apply across an entire session or agent lifecycle. Think of CI1 as the personality and operating parameters of an AI agent distilled into a compact format.

What goes into a CI1 encoding? Typically you'll find behavioral flags that control how the agent operates, reasoning parameters that specify how deeply the agent should think through problems, identity metadata that describes who the agent is and what role it's playing, operational constraints that limit or enable certain behaviors, and header policies that control how the agent formats its outputs.

Here's an example of a CI1 encoding:

```
CI1|SID=7E96|P=Violator-Actual|Ver=2.0|B=B0+B3+B5|MT=d:3|L=on|DR=auto|C=light|HdrF=Stack:Violator-Actual;Model:Claude-3
```

Let me walk through this encoding field by field so you understand how the compression works and what information is preserved. The encoding starts with the format identifier CI1, which immediately tells a parser that this is a configuration instruction rather than a task prompt. This is followed by the pipe character, which VAP Core uses as the primary delimiter between fields.

The SID field contains the session identifier 7E96, which links this CI1 to its originating Sentinel Block. Any artifact that shares the same SID belongs to the same logical session, which is how VAP Core enables coordination across multiple agents or platforms. If you receive a CI1 with SID=7E96 and later receive a CIP2 with SID=7E96, you know they're meant to work together.

The P field specifies the profile, in this case Violator-Actual. The profile identifies which behavioral template or agent personality is being used. Different profiles might have different reasoning styles, communication preferences, or operational constraints. The Ver field indicates which version of the configuration format is being used, which matters for forward and backward compatibility as the protocol evolves.

The B field contains behavior flags, which are compact identifiers for specific behavioral modes. In this example, B=B0+B3+B5 indicates that three specific behavior modes are active. The flags are joined with plus signs to indicate they're all enabled simultaneously. Each flag corresponds to a specific behavior defined in the VAP Core specification. For example, B0 might control precision requirements, B3 might enable or disable certain types of fact-checking, and B5 might govern how the agent handles uncertainty.

The MT field specifies MicroTrace settings, which control the depth of reasoning traces the agent should produce. The notation MT=d:3 means MicroTrace with depth equals three, indicating that the agent should show three levels of reasoning depth in its outputs. Higher depth values produce more detailed explanations of the agent's reasoning process, which is valuable for debugging and auditability but increases output verbosity.

The L field controls the Ledger, which is VAP Core's evidence tracking system. The notation L=on indicates that ledger recording is enabled, meaning the agent will maintain a structured record of claims, evidence, and verification status. This is crucial for applications where you need to trace how the agent arrived at specific conclusions or verify that outputs meet quality standards.

The DR field configures the Decision Record system with the value "auto," meaning the agent will automatically generate decision records showing what options were considered and why specific choices were made. This automatic mode is appropriate for most use cases, though you can also configure manual mode if you want finer control over when decision records are generated.

The C field sets the Critique level to "light," which means the agent will perform lightweight self-evaluation of its outputs, identifying obvious failure modes or weaknesses without doing extensive adversarial analysis. You can adjust this setting to "heavy" for more thorough self-critique or "off" to disable it entirely if you're confident in the agent's outputs or want to minimize processing time.

Finally, the HdrF field contains header formatting instructions using a semicolon-separated substructure. This example shows Stack:Violator-Actual;Model:Claude-3, which tells the agent to include stack trace information in headers and note that it's running on the Claude-3 model. Header formatting is useful for logging and debugging complex multi-agent systems where you need to understand the execution path.

### CIP2: Custom Instruction Prompts for Task-Level Directives

While CI1 handles persistent configuration, CIP2 (Custom Instruction Prompt version two) encodes transient task-level instructions. This is where you specify what you want the agent to do right now, in this specific invocation. CIP2 is designed to be compact yet expressive enough to encode complex task specifications with explicit reasoning contracts.

A CIP2 encoding typically includes the task description, context about what domain or data you're working with, constraints on how the task should be performed, the desired output format, explicit reasoning requirements, and any length or resource limits. The magic of CIP2 is that it can encode all of this information in a form that's dramatically more compact than natural language while being completely unambiguous about what's expected.

Here's a real example of a CIP2 encoding:

```
CIP2|SID=7E96|P=Violator-Actual|CTX=GITS:SAC|TASK=analyze_outfit_symbolism|CONS=concise+accurate+traced|TONE=analytical|OUT=essay+trace|REQ=Trace,Ledger,Decision,Critique|MAX=400
```

This encoding compresses what would naturally be written as: "Analyze the symbolism of Major Kusanagi's outfits in Ghost in the Shell: Stand Alone Complex. Be concise, accurate, and include reasoning traces. Use an analytical tone. Output should be an essay with trace information. Make sure to include reasoning traces, maintain a claim ledger, document your decision process, and provide a self-critique. Limit your response to four hundred words."

Let me explain how this compression works field by field. The format identifier CIP2 tells the parser this is a task prompt rather than configuration. The SID links to the session, and the P field specifies the profile, exactly like in CI1. These consistency patterns make VAP Core easy to parse because the same fields always appear in the same order with the same semantics.

The CTX field provides context about what domain we're working in. The notation GITS:SAC is a compact way to specify "Ghost in the Shell: Stand Alone Complex" using a well-understood abbreviation. Context fields can be hierarchical, so you might see things like CTX=Python:Django:Authentication to specify you're working with Python code, specifically Django framework, specifically authentication functionality. This hierarchical context helps the agent activate the right domain knowledge without requiring lengthy explanations.

The TASK field specifies what action the agent should perform. In this case, analyze_outfit_symbolism clearly indicates we want symbolic analysis of clothing choices. Task names use underscores instead of spaces to avoid parsing ambiguities. Well-chosen task names should be self-documenting; someone reading analyze_outfit_symbolism should immediately understand what's being requested even without seeing the context.

The CONS field encodes constraints using plus signs to join multiple requirements. The value concise+accurate+traced tells the agent three things: keep the response concise rather than verbose, prioritize accuracy over speculation, and include reasoning traces showing how conclusions were reached. These constraints shape the character of the response without needing lengthy explanations about style preferences.

The TONE field specifies the desired communication style. The value "analytical" indicates formal analysis with logical structure and evidence-based reasoning. Other common tones might include "casual" for informal explanation, "technical" for expert-to-expert communication, or "pedagogical" for teaching contexts. Tone is important because the same factual content can be presented very differently depending on audience and purpose.

The OUT field describes the expected output format using a plus-sign-joined structure like the constraints field. The value essay+trace indicates the agent should produce an essay-style response (coherent prose with introduction, body, and conclusion) that includes trace information (explicit reasoning steps). Other output formats might include "bullet_list" for structured summaries, "table" for comparative data, or "code" for implementations.

The REQ field is one of the most powerful aspects of CIP2 because it specifies explicit reasoning requirements that the agent must satisfy. The value Trace,Ledger,Decision,Critique is a comma-separated list of four reasoning artifacts that must be present in the response. Trace means show your reasoning steps. Ledger means maintain a record of claims and evidence. Decision means document what options you considered and why you chose this approach. Critique means evaluate potential weaknesses in your own output. By making these requirements explicit in the encoding, CIP2 transforms prompts from suggestions into contracts with verifiable compliance.

Finally, the MAX field sets a maximum output length. The value 400 indicates the response should not exceed four hundred words. This constraint helps prevent the agent from producing excessively long responses when you need concise answers, and it also makes outputs more predictable in terms of token consumption and processing time.

### How the Pieces Fit Together

Now that you understand the three core components, let me explain how they work together in practice. A typical VAP Core workflow starts with generating a Sentinel Block that establishes session identity. Then you create a CI1 encoding that specifies the persistent behavioral configuration for your agent. Finally, you create one or more CIP2 encodings for specific tasks you want the agent to perform.

The key insight is that the SID links everything together. When you see artifacts with the same SID, you know they're part of the same logical session and should be interpreted in context with each other. If an agent receives a CIP2 with SID=7E96, it should look for a CI1 with the same SID to understand what behavioral configuration applies. This linking mechanism enables sophisticated coordination patterns that would be difficult to achieve with standalone prompts.

---

## How VAP Core Encoding Works

Understanding the encoding process helps you write better VAP Core artifacts and debug issues when things don't work as expected. The encoding process follows a systematic transformation pipeline that takes human-readable configuration or instructions and compresses them into the micro-format representation.

### The Flattening Step

The first transformation is flattening hierarchical data into a linear sequence of key-value pairs. In most configuration formats like JSON or YAML, you express hierarchy through nesting. For example, you might write something like:

```yaml
reasoning:
  microtrace:
    depth: 3
  ledger: enabled
```

VAP Core flattens this structure by concatenating the path to each value with the value itself, using specific delimiters to preserve the semantic structure. The flattening rules are straightforward: top-level key-value pairs are separated by pipe characters, nested structures use semicolons to separate sub-pairs within a value, and lists use commas or plus signs depending on whether order matters.

The flattened version of that YAML example would be: `MT=d:3|L=on`

Notice how the hierarchy is collapsed but still readable. The MT mnemonic represents the full path "reasoning.microtrace," and the notation d:3 represents depth equals three. Similarly, L=on represents "reasoning.ledger: enabled" in a form that's dramatically more compact but still unambiguous.

### The Escaping Mechanism

Because VAP Core uses specific characters as delimiters (pipe, semicolon, comma, plus, equals), you need a way to include those characters as literal values without them being interpreted as structure. This is where escaping comes in. The escaping rules in VAP Core are simple and borrowed from common Unix conventions: any reserved delimiter character can be preceded by a backslash to indicate it should be treated as literal text rather than structure.

For example, if you need to encode a task that includes a pipe character in its description, you would write: `TASK=analyze text\|symbol relationships`

The backslash before the pipe tells the parser not to interpret that pipe as a field separator. When decoding, the parser removes the backslash and restores the literal pipe character in the output.

There's one additional escaping rule you need to know: backslash itself must be escaped. To include a literal backslash in a value, you write two backslashes: `\\`. This prevents ambiguity about whether a backslash is an escape character or literal text.

### The Mnemonic Dictionary

One of the key compression techniques in VAP Core is the use of a standardized mnemonic dictionary that maps short codes to longer descriptive phrases. This dictionary is versioned and frozen, meaning that once a mnemonic is defined in a particular version of the specification, it never changes. This stability is crucial for deterministic decoding.

For example, the mnemonic MT always expands to MicroTrace, L always expands to Ledger, DR always expands to DecisionRecord, and C always expands to Critique. These mappings are defined in the VAP Core specification and are the same for everyone using the protocol. You don't need to include the dictionary in your encoded artifacts because it's part of the specification itself.

The dictionary approach gives you dramatic compression for common concepts while maintaining readability. Someone familiar with VAP Core can look at `MT=d:3|L=on|DR=auto|C=light` and immediately understand what configuration is being expressed, even though the encoding is much shorter than the equivalent natural language description.

If you need to encode domain-specific concepts that aren't in the standard dictionary, VAP Core provides an extension mechanism. Custom mnemonics are prefixed with X_ to indicate they're extensions rather than standard codes. For example, if you're working in a medical domain and want a mnemonic for patient_consent_verified, you might use X_PCV. The X_ prefix signals to parsers that they should look for domain-specific definitions rather than assuming this is a standard mnemonic that somehow got corrupted.

### Deterministic Key Ordering

One subtle but important aspect of VAP Core encoding is that keys appear in a deterministic order. When encoding a CI1 or CIP2, the implementation always outputs fields in the same sequence: format identifier, then SID, then P, then Ver, and so on. This deterministic ordering serves two purposes.

First, it makes encoded artifacts easier to compare visually. If you're looking at two CI1 encodings and trying to understand how they differ, having the fields in the same order means you can scan across them field by field rather than hunting for where each piece of information appears. This seems like a minor convenience, but it adds up significantly when you're debugging complex configurations.

Second, deterministic ordering makes the encoding itself part of the artifact's identity. If you hash a VAP Core encoding, you get a unique identifier for that specific configuration. Two encodings that differ in any way will produce different hashes, while two encodings that are semantically identical will produce the same hash. This property is useful for deduplication, caching, and integrity verification.

### Round-Trip Validation

One of the most important properties of VAP Core encoding is that it's completely reversible. If you encode something and then decode it, you should get back exactly what you started with, character for character. This round-trip property is essential for reliability and trust in the protocol.

The reference implementation includes extensive tests that verify round-trip fidelity for all supported field types and edge cases. These tests encode various configurations, decode the results, and assert that the decoded form matches the original input exactly. Any failure in round-trip validation would indicate either a bug in the encoder, a bug in the decoder, or an ambiguity in the specification that needs to be resolved.

When you're working with VAP Core, you should periodically validate that your encodings are reversible by running them through both encode and decode operations and comparing the results. This practice helps catch issues like accidentally using reserved characters without escaping them or creating malformed structures that happen to parse but don't preserve semantics correctly.

---

## Practical Usage Examples

Now that you understand the theory, let me show you how to actually use VAP Core in practice. I'll walk through several common scenarios, starting simple and building up to more sophisticated patterns.

### Example 1: Simple Task Encoding

Let's say you want to encode a straightforward task: reviewing a piece of code for security issues. In natural language, you might write:

"Review this Python code for security vulnerabilities. Be thorough and list any issues you find. Include your reasoning for why each issue is a problem."

Here's how you would encode this as a CIP2:

```
CIP2|SID=A1B2|TASK=security_review|CTX=Python|CONS=thorough|OUT=issue_list|REQ=Trace|MAX=500
```

Notice how the encoding is dramatically shorter (eighty-one characters versus one hundred sixty-one characters for the natural language version) while preserving all the semantic content. The SID=A1B2 links to a session. The TASK clearly states we want a security review. The CTX=Python tells the agent we're working with Python code. The CONS=thorough indicates we want comprehensive analysis rather than quick scanning. The OUT=issue_list specifies we want structured output as a list of issues. The REQ=Trace requires reasoning traces showing why each issue matters. And MAX=500 limits the response to five hundred words.

If you decode this CIP2, a compliant agent knows exactly what to do without any ambiguity about expectations or output format. This explicitness is one of the main benefits of VAP Core over natural language prompts, which often leave room for interpretation about what's wanted.

### Example 2: Creating a Persistent Agent Configuration

Now let's consider a more complex scenario where you want to configure an agent with specific persistent behavior. You want an agent that always shows its reasoning, maintains evidence tracking, performs lightweight self-critique, and operates at reasoning depth three. In a configuration file, this might look like:

```yaml
profile: AnalyticalAgent
reasoning:
  microtrace:
    depth: 3
  ledger: enabled
  critique: light
behavior_flags:
  - precision_mode
  - fact_check_enabled
  - show_reasoning
```

The CI1 encoding for this configuration would be:

```
CI1|SID=C3D4|P=AnalyticalAgent|Ver=2.0|B=B0+B2+B4|MT=d:3|L=on|C=light
```

This encoding is ninety characters compared to approximately two hundred characters for the YAML version, and it captures all the same information in a form that can be directly inserted into a persistent instruction field. The behavior flags B0+B2+B4 map to precision_mode, fact_check_enabled, and show_reasoning respectively according to the VAP Core mnemonic dictionary.

### Example 3: Multi-Agent Coordination

One of the more sophisticated uses of VAP Core is coordinating multiple agents working on related tasks. Imagine you have three agents: one analyzing data, one validating the analysis, and one synthesizing the results. All three agents need to work within the same session so their outputs can be combined coherently.

You start by creating a Sentinel Block for the session:

```
SENTINEL:E5F6:(ab12cd34-ef56-7890-abcd-1234567890ab|DataPipeline|2025-11-05T16:20Z|i:[data_analysis]|2i:[multi_agent_synthesis]|Tools:15|Sources:3)
```

Then each agent gets a CIP2 with the same SID but different tasks:

Agent A (Analysis):
```
CIP2|SID=E5F6|TASK=analyze_dataset|CTX=sales_data:Q4_2024|CONS=thorough+quantitative|OUT=statistical_summary|REQ=Trace,Ledger
```

Agent B (Validation):
```
CIP2|SID=E5F6|TASK=validate_analysis|CTX=sales_data:Q4_2024|CONS=critical+evidence_based|OUT=validation_report|REQ=Trace,Critique
```

Agent C (Synthesis):
```
CIP2|SID=E5F6|TASK=synthesize_findings|CTX=sales_data:Q4_2024|CONS=comprehensive+actionable|OUT=executive_summary|REQ=Decision,Critique|MAX=800
```

All three CIP2 encodings share SID=E5F6, which links them to the same logical session. When you collect the outputs from all three agents, you can verify they all trace back to the same Sentinel Block by checking that their SIDs match. This provenance tracking becomes essential when debugging issues or auditing the decision chain in complex multi-agent workflows.

### Example 4: Iterative Refinement

Sometimes you need to refine an instruction based on initial results. VAP Core makes this pattern explicit through version tracking and SID inheritance. Let's say you start with a broad analytical task:

```
CIP2|SID=G7H8|TASK=market_analysis|CTX=tech_sector|CONS=broad_overview|OUT=report|REQ=Trace
```

After reviewing the initial output, you realize you need more depth on a specific aspect. Rather than starting over, you create a refinement CIP2 that maintains the same SID but focuses the task:

```
CIP2|SID=G7H8|TASK=deep_dive_analysis|CTX=tech_sector:cloud_computing|CONS=detailed+technical|OUT=technical_report|REQ=Trace,Ledger,Decision|MAX=1200
```

By keeping the same SID, you signal that this refined task is a continuation of the original analysis rather than an independent request. Agents or logging systems that understand VAP Core can recognize these artifacts as belonging to the same analytical thread and maintain context accordingly.

---

## Installation and Basic Usage

Let me walk you through how to actually start using VAP Core in your projects. The reference implementation is written in Python and designed to be easy to integrate whether you're building a command-line tool, a web service, or embedding VAP Core into a larger application.

### Installing the Package

The simplest way to get started is installing via pip:

```bash
pip install wraithspec-vap
```

This installs both the Python library for programmatic use and the command-line tool for interactive work. If you prefer to install from source for development purposes, you can clone the repository and install in editable mode:

```bash
git clone https://github.com/dmaynor/WraithSpec.git
cd WraithSpec
pip install -e .
```

The editable installation lets you modify the source code and immediately see changes without reinstalling, which is useful if you're contributing to the project or adapting it for specialized use cases.

### Command-Line Interface

The package includes a command-line tool called `vap-micro` that lets you encode, decode, and validate VAP Core artifacts without writing any code. This is perfect for experimentation, debugging, and quick one-off tasks.

To encode a simple CIP2 from the command line:

```bash
vap-micro encode --kind CIP2 \
  --field SID=TEST \
  --field TASK=example_task \
  --field CTX=demo \
  --field OUT=text
```

This command produces a CIP2 encoding with the specified fields. You can add as many `--field` arguments as you need to build up the complete encoding. The output is printed to stdout, so you can pipe it to other tools or save it to a file.

To decode an existing artifact:

```bash
vap-micro decode "CIP2|SID=TEST|TASK=example_task|CTX=demo|OUT=text"
```

The decoder outputs a human-readable representation of the artifact showing all the parsed fields and their values. This is useful when you receive a VAP Core encoding and want to understand what it contains without manually parsing the syntax.

To validate that an encoding is well-formed:

```bash
vap-micro validate "CIP2|SID=TEST|TASK=example_task"
```

The validator checks that the encoding follows the VAP Core grammar, includes all required fields for its type (CI1 or CIP2), properly escapes reserved characters, and uses valid mnemonic codes. If validation fails, you get an error message explaining what's wrong.

### Programmatic Usage

For integrating VAP Core into applications, you'll typically use the Python API directly. Here's a basic example that shows the core encoding and decoding operations:

```python
from wraithspec import CIP2Encoder, CI1Encoder, SentinelBlock

# Create a Sentinel Block for the session
sentinel = SentinelBlock.generate(
    profile="MyAgent",
    intent="task_processing",
    sub_intent="automated_analysis"
)

print(f"Created session with SID: {sentinel.sid}")

# Encode a CIP2 task instruction
task_config = {
    "sid": sentinel.sid,
    "task": "analyze_data",
    "context": "financial:quarterly_results",
    "constraints": ["thorough", "quantitative"],
    "output": "report",
    "requirements": ["Trace", "Ledger", "Decision"],
    "max_words": 500
}

cip2_encoded = CIP2Encoder.encode(task_config)
print(f"Encoded CIP2: {cip2_encoded}")

# Decode it back to verify
decoded = CIP2Encoder.decode(cip2_encoded)
print(f"Decoded fields: {decoded}")

# Verify round-trip fidelity
assert decoded["task"] == task_config["task"]
assert decoded["context"] == task_config["context"]
```

This example demonstrates the complete workflow: generating a Sentinel Block to establish session identity, encoding a task configuration into CIP2 format, decoding the result to extract the fields, and validating that the round-trip preserved all the information correctly.

The encoder functions handle all the details of field ordering, delimiter escaping, mnemonic expansion, and format validation. You provide a dictionary of fields in human-readable form, and the encoder produces the compact VAP Core representation. The decoder reverses this process, taking the compact encoding and producing a dictionary that matches what you put in.

### Working with CI1 Configuration

CI1 encoding works similarly to CIP2 but with different field requirements:

```python
from wraithspec import CI1Encoder

# Encode persistent agent configuration
config = {
    "sid": sentinel.sid,
    "profile": "AnalyticalAgent",
    "version": "2.0",
    "behavior_flags": ["B0", "B2", "B4"],
    "microtrace": {"depth": 3},
    "ledger": True,
    "critique": "light"
}

ci1_encoded = CI1Encoder.encode(config)
print(f"Encoded CI1: {ci1_encoded}")

# Decode and use
decoded_config = CI1Encoder.decode(ci1_encoded)
print(f"Agent profile: {decoded_config['profile']}")
print(f"Reasoning depth: {decoded_config['microtrace']['depth']}")
```

Notice how the encoder automatically handles type conversions. You provide a boolean True for the ledger field, and it encodes as "on" in the micro-format. When decoded, it comes back as True. Similarly, lists like the behavior flags get joined with plus signs in the encoding and split back into lists during decoding.

### Integrating with LLM APIs

The real power of VAP Core comes when you integrate it with large language model APIs. Here's an example showing how to use VAP Core encodings as part of LLM requests:

```python
import anthropic

# Create CIP2 task encoding
cip2 = CIP2Encoder.encode({
    "sid": "DEMO",
    "task": "analyze_symbolism",
    "context": "literature:symbolism",
    "constraints": ["concise", "analytical"],
    "output": "essay",
    "requirements": ["Trace", "Critique"],
    "max_words": 300
})

# Use it in an API call
client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    system=f"Task specification: {cip2}",  # VAP Core in system context
    messages=[
        {
            "role": "user",
            "content": "Analyze the symbolism of doors in Gothic literature"
        }
    ]
)

print(message.content[0].text)
```

In this pattern, the CIP2 encoding goes into the system context where it provides persistent instruction about how the task should be performed. The actual content (the specific text to analyze) goes in the user message. This separation between task specification and task content is one of the key advantages of VAP Core—you can reuse the same task encoding across many different content inputs.

---

## Advanced Patterns and Best Practices

Once you're comfortable with the basics, there are several advanced patterns that can make your use of VAP Core more sophisticated and powerful.

### Pattern: Hierarchical Context Building

You can build hierarchical context by using colon-separated notation in the CTX field:

```python
# Broad context
CIP2Encoder.encode({...,"context": "programming"})

# More specific
CIP2Encoder.encode({...,"context": "programming:Python"})

# Very specific
CIP2Encoder.encode({...,"context": "programming:Python:async"})

# Domain-specific hierarchy
CIP2Encoder.encode({...,"context": "medical:cardiology:arrhythmia"})
```

This hierarchical structure lets agents understand the scope of their task. A query about Python async programming is different from a general programming question, and encoding this specificity helps the agent activate the right knowledge and provide more targeted responses.

### Pattern: Constraint Composition

The constraints field supports composition using plus signs, and order can matter semantically:

```python
# These constraints interact
"constraints": ["fast", "approximate"]  # Quick rough answer
"constraints": ["thorough", "precise"]  # Careful detailed answer

# Order can convey priority
"constraints": ["accurate", "concise"]  # Accuracy first, brevity second
"constraints": ["concise", "accurate"]  # Brevity first, accuracy second
```

Think carefully about which constraints you combine and in what order. Some constraint combinations are contradictory (like "brief" and "comprehensive"), while others are synergistic (like "analytical" and "evidence_based"). The agent will try to satisfy all specified constraints, but if they conflict, having them in priority order helps resolve the tension.

### Pattern: Reasoning Contract Specification

The requirements field (REQ) is where you specify explicit reasoning artifacts that must be present in the output. This is one of the most powerful features of VAP Core because it transforms prompts from suggestions into verifiable contracts:

```python
# Minimal reasoning
"requirements": ["Trace"]  # Just show your steps

# Standard reasoning
"requirements": ["Trace", "Ledger"]  # Show steps + track claims

# Full reasoning
"requirements": ["Trace", "Ledger", "Decision", "Critique"]  # Everything

# Custom combinations
"requirements": ["Decision", "Critique"]  # Focus on evaluation, skip trace
```

Each requirement corresponds to a specific type of reasoning artifact. Trace means the agent should show its reasoning steps as it works through the problem. Ledger means maintaining a structured record of claims and the evidence supporting them. Decision means documenting what options were considered and why a particular approach was chosen. Critique means evaluating weaknesses in the agent's own output and suggesting improvements.

By making these requirements explicit in the encoding, you can programmatically verify that outputs include the required artifacts. This is essential for regulated domains where you need audit trails or for debugging situations where you need to understand why an agent produced a particular output.

### Pattern: Progressive Refinement

A common workflow involves starting with a broad CIP2, reviewing the output, and then creating a more focused follow-up CIP2 that maintains the same SID:

```python
# Initial broad analysis
initial_cip2 = CIP2Encoder.encode({
    "sid": "PROJ1",
    "task": "market_analysis",
    "context": "tech_sector",
    "output": "overview"
})

# After review, dive deeper on specific aspect
refined_cip2 = CIP2Encoder.encode({
    "sid": "PROJ1",  # Same SID links to initial analysis
    "task": "detailed_analysis",
    "context": "tech_sector:AI:LLM_providers",
    "constraints": ["technical", "competitive"],
    "output": "detailed_report",
    "requirements": ["Trace", "Decision"]
})
```

By maintaining the same SID across the refinement, you create a logical thread that tools can track. A logging system could collect all artifacts with SID=PROJ1 and reconstruct the entire analytical process from initial exploration to final detailed report.

### Best Practice: Always Validate Before Use

Before using a VAP Core encoding in production, validate it to catch errors early:

```python
from wraithspec import validate_encoding

cip2 = CIP2Encoder.encode(config)

# Validate before sending to LLM
if validate_encoding(cip2):
    # Use it
    response = llm_api.call(system=cip2, ...)
else:
    # Handle validation failure
    logger.error(f"Invalid CIP2 encoding: {cip2}")
```

Validation catches malformed encodings, missing required fields, invalid mnemonic codes, and unescaped reserved characters. Catching these errors before making expensive API calls saves both money and debugging time.

### Best Practice: Use Meaningful Task Names

Task names should be self-documenting. Compare these examples:

```python
# Unclear
"task": "process"  # Process what? How?

# Clear
"task": "security_audit"  # Obviously about security
"task": "performance_optimization"  # Obviously about performance
"task": "sentiment_analysis"  # Obviously about sentiment
```

Good task names make artifacts readable without needing extensive documentation. Anyone looking at a CIP2 with TASK=sentiment_analysis immediately understands what's being requested, while TASK=process requires additional context to interpret.

### Best Practice: Document Your Context Hierarchies

If you're using hierarchical context notations extensively, document your hierarchy structure:

```python
# In your project documentation:
# Context Hierarchy:
# - programming:Python:async - Python async/await patterns
# - programming:Python:data - Data manipulation (pandas, numpy)
# - programming:Python:web - Web frameworks (Django, Flask)
# - programming:JavaScript:react - React framework
# - programming:JavaScript:node - Node.js backend
```

This documentation helps maintain consistency across your encodings and makes it easier for new team members to understand your context notation conventions.

---

## Understanding the Benefits

Now that you've seen how VAP Core works, let me articulate why this approach is valuable compared to alternatives you might consider.

### Benefit: Dramatic Compression

The most obvious benefit is compression. VAP Core encodings are typically sixty to sixty-five percent shorter than equivalent natural language instructions. This matters because it lets you fit sophisticated behavioral frameworks into restricted context windows that would otherwise force you to oversimplify.

Consider a complex agent configuration that specifies reasoning depth, evidence tracking, self-critique requirements, behavioral flags, output formatting, and operational constraints. Written naturally, this might consume two thousand characters. Encoded with VAP Core, it might be seven hundred characters. The difference between fitting and not fitting within a thousand-character limit can be the difference between having a capable agent and having to remove features until it's barely useful.

### Benefit: Deterministic Interpretation

Natural language is inherently ambiguous. When you write "be thorough," different interpreters might have different ideas about what thorough means. When you write "include reasoning," it's unclear whether that means informal explanation or formal logical steps. This ambiguity leads to inconsistent outputs that are hard to debug.

VAP Core encodings are completely unambiguous. When a compliant agent sees REQ=Trace,Ledger, it knows exactly what artifacts to produce. There's no room for interpretation about whether "trace" means informal reasoning or structured steps—the specification defines it precisely. This determinism is crucial for reproducibility and reliability in production systems.

### Benefit: Auditability and Provenance

The Sentinel Block and SID mechanism provide built-in provenance tracking that would be difficult to achieve with ad-hoc approaches. Every artifact carries metadata about when it was created, who created it, what session it belongs to, and what resources were available. This metadata trail is invaluable for debugging, auditing, and compliance in regulated industries.

Imagine you're operating a fleet of AI agents that make recommendations affecting financial decisions. If a recommendation turns out to be wrong, you need to trace back through the entire decision chain to understand what went wrong. With VAP Core, every artifact has a SID linking it to its session, every session has a Sentinel Block recording the configuration, and every output includes the reasoning artifacts that led to the recommendation. This complete audit trail would be extremely difficult to maintain with unstructured natural language prompts.

### Benefit: Multi-Agent Coordination

The SID-based coordination mechanism makes it straightforward to implement multi-agent workflows. When you need multiple agents working on related tasks, you generate one Sentinel Block and create CIP2 encodings for each agent with the same SID. Now you have a coordination primitive that requires no centralized state management or complex distributed systems infrastructure.

This simplicity is deceptive. Traditional multi-agent coordination often requires message brokers, shared databases, or complex consensus protocols. VAP Core sidesteps all that complexity by embedding coordination information directly in the artifacts themselves. Any agent that understands VAP Core can participate in coordinated workflows without needing access to shared infrastructure.

### Benefit: Programmatic Verifiability

Because VAP Core encodings have explicit structure and requirements fields, you can programmatically verify that outputs satisfy contracts. If a CIP2 specifies REQ=Trace,Ledger,Critique, you can write code that scans the output and checks whether trace sections, ledger tables, and critique paragraphs are present.

This verifiability enables quality control pipelines that would be difficult with natural language prompts. You can reject outputs that don't include required artifacts, automatically route outputs for human review when verification fails, and track compliance rates across different agents or models. These capabilities are essential for production deployments where you can't manually inspect every output.

---

## Contributing and Extending VAP Core

VAP Core is designed to be extensible while maintaining a stable core specification. If you're interested in contributing to the project or adapting it for specialized domains, here's what you need to know.

### The Extension Mechanism

The standard mnemonic dictionary covers common concepts, but you'll inevitably encounter domain-specific needs. The extension mechanism lets you define custom mnemonics without conflicting with the standard dictionary. Custom mnemonics use the X_ prefix to indicate they're extensions:

```python
# Standard mnemonics (no prefix)
"MT=d:3"  # MicroTrace depth=3
"L=on"    # Ledger enabled

# Custom extensions (X_ prefix)
"X_MED_CONSENT=verified"  # Medical consent verified (custom)
"X_FIN_RISK=high"         # Financial risk level (custom)
```

When implementing extensions, document them clearly so others can understand your encoding conventions. Consider contributing widely useful extensions back to the main specification so they can become standardized mnemonics in future versions.

### Adding New Reasoning Artifacts

The REQ field currently supports Trace, Ledger, Decision, and Critique as standard reasoning artifacts. If you develop new reasoning patterns that should be part of the requirement contract, you can propose them for inclusion in the next version of the specification.

For example, you might find that your domain needs "ProofOfWork" artifacts showing that the agent did proper research, or "CounterfactualAnalysis" artifacts exploring what would have happened with different assumptions. Document these new artifact types clearly, show examples of what they look like in practice, and explain why they're valuable additions to the standard repertoire.

### Implementing in Other Languages

The Python reference implementation demonstrates the core algorithms, but VAP Core is designed to be language-agnostic. If you want to implement encoders and decoders in JavaScript, Go, Rust, or any other language, the specification provides everything you need.

The key to a correct implementation is ensuring round-trip fidelity. Your encoder and decoder should satisfy the property that `decode(encode(x)) == x` for all valid inputs. The Python implementation includes a comprehensive test suite that you can use as a conformance test for other implementations. If your implementation passes the same test cases, you can be confident it's compatible with the reference implementation.

### Reporting Issues and Requesting Features

If you encounter bugs, have questions about the specification, or want to propose new features, the GitHub repository has an issue tracker where you can submit detailed reports. When reporting issues, include the VAP Core encoding that exhibits the problem, the expected behavior, the actual behavior you observed, and any relevant error messages or logs.

For feature requests, explain the use case motivating the feature, show examples of how you would use it, and discuss why existing features don't adequately address your needs. Feature proposals with clear motivation and concrete examples are much more likely to be adopted than vague requests for new capabilities.

---

## Conclusion and Next Steps

You now have a comprehensive understanding of WraithSpec VAP Core: what it is, why it exists, how it works, and how to use it effectively. The protocol provides a systematic way to compress complex behavioral configurations and task instructions while maintaining full semantic fidelity, deterministic interpretation, and provenance tracking.

If you're new to VAP Core, start by installing the package and experimenting with the command-line tools. Encode some simple tasks, decode them to see the structure, and verify that round-trip encoding preserves information correctly. Once you're comfortable with the basics, try integrating VAP Core into a small project where you're working with LLM APIs. Experience the benefit of explicit reasoning contracts and compressed context in real usage before scaling up to more sophisticated applications.

If you're already familiar with VAP Core and want to contribute, consider implementing support in a new language, documenting usage patterns in your domain, contributing to the test suite, or proposing extensions for specialized use cases. The project benefits from diverse perspectives and real-world validation across different problem domains.

The VAP Core specification continues to evolve based on community feedback and real-world usage. By participating in this evolution, you help shape a protocol that makes AI systems more reliable, auditable, and capable of sophisticated coordination. Welcome to the WraithSpec community.