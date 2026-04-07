"""
Capstone: RFP/SOW Response Generator
=====================================
Multi-agent pipeline that reads an RFP, searches past proposals,
and generates a tailored response with quality review loops.
"""

# ── Step A: Sample RFP Document ──────────────────────────────────────────────

SAMPLE_RFP = """
REQUEST FOR PROPOSAL
Meridian Healthcare Systems
RFP-2024-MH-0847

TITLE: AI-Powered Analytics Platform Enhancement

ISSUING ORGANIZATION: Meridian Healthcare Systems
CONTACT: James Rivera, VP of Technology, j.rivera@meridianhc.com
SUBMISSION DEADLINE: October 15, 2024
BUDGET RANGE: $800,000 - $1,200,000

1. BACKGROUND

Meridian Healthcare Systems operates 14 hospitals and 52 outpatient clinics
across the Midwest region, serving approximately 2.3 million patients annually.
We currently use Acme Corporation's Product Alpha for our core analytics
needs and have been a customer since 2021 (current contract: $1.2M ACV).

We are seeking to enhance our analytics capabilities with AI-powered features
to improve clinical decision support, operational efficiency, and patient
outcome prediction.

2. SCOPE OF WORK

The selected vendor shall provide:

2.1 Clinical Decision Support Module
- Real-time patient risk scoring using historical EHR data
- Predictive models for readmission risk (target: 30-day readmission)
- Integration with existing Epic EHR system via FHIR APIs
- Dashboard for clinical staff with configurable alert thresholds

2.2 Operational Analytics Enhancement
- AI-powered demand forecasting for staffing and resource allocation
- Automated anomaly detection for billing and coding patterns
- Natural language query interface for non-technical users
- Integration with existing Product Alpha dashboards

2.3 Patient Outcome Analytics
- Population health trend analysis across all 14 facilities
- Social determinants of health (SDOH) data integration
- Predictive modeling for chronic disease management
- Outcome tracking and reporting for value-based care contracts

3. REQUIREMENTS

3.1 Technical Requirements
- Must integrate with existing Product Alpha deployment
- HIPAA-compliant data handling and storage
- SOC 2 Type II certification required
- Support for on-premises and hybrid cloud deployment
- API-first architecture for future extensibility
- Minimum 99.9% uptime SLA

3.2 Data Requirements
- Must process structured (EHR) and unstructured (clinical notes) data
- Support for HL7 FHIR R4 data standards
- Data retention per healthcare regulatory requirements
- De-identification capabilities for research datasets

3.3 Team Requirements
- Dedicated project manager
- Healthcare domain expertise (minimum 3 years)
- Data science team with clinical NLP experience
- 24/7 support during go-live and 90-day stabilization period

4. PROPOSAL FORMAT

Respondents must include the following sections:
a) Technical Approach
b) Healthcare Industry Experience
c) Proposed Team and Qualifications
d) Project Timeline and Milestones
e) Cost Proposal and Value Justification

5. EVALUATION CRITERIA

- Technical capability and approach: 30%
- Healthcare experience and domain expertise: 25%
- Team qualifications: 15%
- Timeline feasibility: 15%
- Cost and value: 15%

6. TERMS

- Contract period: 18 months (implementation) + 36 months (support)
- Payment terms: Milestone-based
- IP: All custom models trained on Meridian data remain Meridian property
- Subcontracting: Permitted with prior approval
"""

# ── Step B: Sample Past Proposals for Ingestion ──────────────────────────────

PAST_PROPOSALS = [
    {
        "id": "proposal-midwest-health-2023",
        "title": "Midwest Health Network - Analytics Platform Deployment",
        "category": "healthcare",
        "text": """Acme Corporation proposed a comprehensive analytics deployment for Midwest
Health Network, a 9-hospital system serving 1.4 million patients. The project
included real-time clinical dashboards powered by Product Alpha, integration
with Cerner EHR via FHIR APIs, and predictive models for ED visit forecasting.

Technical approach: We deployed Product Alpha in a hybrid architecture with
on-premises data processing for PHI and cloud-based model training using
de-identified datasets. Our HIPAA-compliant pipeline processed 2.3TB of
historical patient data to train baseline models.

Team: 8-person team including 2 clinical informaticists, 3 data scientists
with healthcare NLP experience, 1 project manager (PMP, healthcare background),
and 2 platform engineers.

Timeline: 14-month implementation with 4 phases: Discovery (2 months),
Core Platform (4 months), AI Model Development (5 months), UAT and Go-Live
(3 months).

Outcome: Deployed on time. ED visit prediction accuracy reached 84%.
30-day readmission model achieved 0.78 AUC. Client renewed for 3 additional years.
Contract value: $1.8M implementation + $600K annual support."""
    },
    {
        "id": "proposal-statewide-insurance-2024",
        "title": "Statewide Insurance Group - Claims Analytics",
        "category": "insurance",
        "text": """Acme Corporation developed an AI-powered claims analytics system for
Statewide Insurance Group to detect fraudulent claims patterns and optimize
claims processing workflows.

Technical approach: Product Alpha served as the analytics foundation with
custom ML models for claims anomaly detection. We implemented natural language
processing to extract information from unstructured claims narratives and
medical records. The system processed 50,000+ claims daily with sub-second
response times.

Integration: REST API architecture connecting to the client's existing
claims management system (Guidewire ClaimCenter). Real-time scoring pipeline
with batch model retraining on weekly cycles.

Team: 6-person team including 2 data scientists, 1 NLP specialist,
1 project manager, and 2 platform engineers.

Timeline: 10-month implementation. Phases: Discovery (6 weeks), Platform
Setup (8 weeks), Model Development (12 weeks), Integration and Testing
(8 weeks), Go-Live (6 weeks).

Outcome: 34% improvement in fraud detection rates. Claims processing time
reduced by 22%. ROI achieved within 8 months of go-live.
Contract value: $950K implementation + $320K annual support."""
    },
    {
        "id": "proposal-regional-medical-2024",
        "title": "Regional Medical Center - Patient Flow Optimization",
        "category": "healthcare",
        "text": """Acme Corporation built a patient flow optimization system for Regional
Medical Center, a 450-bed facility with 180,000 annual patient encounters.

Technical approach: Deployed Product Alpha with custom predictive modules
for patient flow management. Key components included: (1) admission prediction
models using historical patterns and external data (weather, flu trends),
(2) real-time bed management dashboards with AI-recommended assignments,
(3) discharge prediction to optimize downstream capacity planning.

Data integration: Connected to Epic EHR via FHIR R4 APIs for real-time
ADT (Admission, Discharge, Transfer) feeds. Integrated SDOH data from
community health databases. All data handling HIPAA-compliant with BAA
in place.

Team: 5-person team including 1 clinical data scientist (PhD, 7 years
healthcare experience), 2 ML engineers, 1 project manager, and 1
integration specialist.

Timeline: 8-month implementation with 3 phases: Foundation (2 months),
Model Development (4 months), Go-Live and Optimization (2 months).

Outcome: 18% reduction in ED boarding time. Bed utilization improved by
12%. Patient satisfaction scores increased 8 points. System processes
500+ real-time events per minute.
Contract value: $720K implementation + $240K annual support."""
    },
]

COMPANY_KNOWLEDGE = [
    {
        "id": "kb-product-alpha-capabilities",
        "title": "Product Alpha Technical Capabilities",
        "category": "product",
        "text": """Product Alpha is Acme Corporation's flagship analytics platform.
Current capabilities include: real-time data processing (up to 100K events/sec),
customizable dashboards with role-based access, ML model hosting and serving,
FHIR R4 and HL7v2 healthcare data standard support, SOC 2 Type II certified,
HIPAA-compliant data handling with BAA support, hybrid cloud deployment
(on-premises + AWS/Azure), API-first architecture with RESTful and GraphQL
endpoints, 99.95% historical uptime over the past 24 months.

Product Alpha Q2 revenue: $12.4M. ARR: $48.2M. Primary competitor: Dataview.
Key differentiator: Healthcare-native data model with pre-built clinical
ontologies."""
    },
    {
        "id": "kb-product-beta-overview",
        "title": "Product Beta Overview",
        "category": "product",
        "text": """Product Beta is Acme Corporation's self-service analytics tool designed
for non-technical users. Features include: natural language query interface
(ask questions in plain English), automated report generation, anomaly
detection and alerting, integration with Product Alpha for data access.

Product Beta Q2 revenue: $3.8M. Churn rate: 4.2% (target: reduce to 3.0%).
Ideal for departmental analytics where technical resources are limited."""
    },
    {
        "id": "kb-team-bios",
        "title": "Acme Corporation Key Personnel",
        "category": "team",
        "text": """Acme Corporation maintains a team of 340+ employees across engineering,
data science, and client services.

Healthcare Practice Lead: Dr. Maria Santos, PhD in Biomedical Informatics,
12 years healthcare IT experience, former CMIO at a 600-bed academic medical
center. Oversees all healthcare client engagements.

VP of Engineering: Raj Patel, 18 years enterprise software experience,
previously VP Engineering at a major EHR vendor. Leads the Product Alpha
platform team.

Director of Data Science: Lin Wei, PhD in Machine Learning, published
researcher in clinical NLP. Team of 28 data scientists, 8 with healthcare
domain expertise.

Client Success: Dedicated healthcare account team with an average of
6 years healthcare analytics experience per team member."""
    },
    {
        "id": "kb-security-compliance",
        "title": "Acme Corporation Security and Compliance",
        "category": "compliance",
        "text": """Acme Corporation security and compliance posture:
- SOC 2 Type II certified (annual audit, no findings in last 3 years)
- HIPAA compliant with Business Associate Agreement (BAA) support
- HITRUST CSF certified
- FedRAMP Moderate (in progress, expected Q1 2025)
- Annual penetration testing by independent third party
- 256-bit AES encryption at rest, TLS 1.3 in transit
- Role-based access control with SAML 2.0 SSO
- Data residency options: US-only, EU, or customer-specified
- Incident response SLA: 1 hour acknowledgment, 4 hour initial response
- 99.95% uptime SLA with financial credits for breach"""
    },
]

# ── Step C: Imports, Configuration, and Infrastructure ───────────────────────

import os
import re
import json
import time
import hashlib
from typing import TypedDict
from datetime import datetime

import anthropic
from openai import OpenAI
from pinecone import Pinecone
from langfuse import Langfuse
from langgraph.graph import StateGraph, END

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from dotenv import load_dotenv

load_dotenv()

# --- Clients ---
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

pii_analyzer = AnalyzerEngine()
pii_anonymizer = AnonymizerEngine()

# --- Constants ---
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_COST_PER_RFP = 2.00  # $2 hard cap per RFP response
MAX_REVISION_CYCLES = 2
MIN_QUALITY_SCORE = 7    # Sections scoring below 7 get revised

COST_PER_INPUT_TOKEN = 3.0 / 1_000_000
COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000

# Pinecone namespace configuration
PROPOSALS_NAMESPACE = "past-proposals"
KNOWLEDGE_NAMESPACE = "company-knowledge"


# --- State Schema ---
class RFPPipelineState(TypedDict):
    rfp_text: str
    sanitized_rfp: str
    requirements: list[dict]
    sections_needed: list[str]
    complexity_score: int
    retrieved_knowledge: dict          # section_name -> list of docs
    draft_sections: dict               # section_name -> draft text
    revision_feedback: dict            # section_name -> feedback text
    quality_scores: dict               # section_name -> {relevance, completeness, accuracy}
    revision_count: int
    metadata: dict
    errors: list[str]
    trace_id: str
    cumulative_cost: float             # Running cost total for hard cap


# --- Utility Functions ---
def embed_text(text: str) -> list[float]:
    """Generate embedding using OpenAI text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> dict:
    """Call Claude and return response with usage metadata."""
    start = time.time()
    response = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = time.time() - start
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)

    return {
        "content": response.content[0].text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
        "latency": elapsed,
    }


def search_pinecone(query: str, namespace: str, top_k: int = 5) -> list[dict]:
    """Search a specific Pinecone namespace."""
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    query_embedding = embed_text(query)
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )
    return [
        {
            "id": match["id"],
            "score": match["score"],
            "text": match["metadata"].get("text", ""),
            "source": match["metadata"].get("source", "unknown"),
            "category": match["metadata"].get("category", "unknown"),
        }
        for match in results["matches"]
    ]


# ── Step D: Document Ingestion ────────────────────────────────────────────────

def ingest_documents():
    """
    Ingest past proposals and company knowledge into Pinecone.
    Run this once before the pipeline.
    """
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

    print("Ingesting past proposals...")
    for proposal in PAST_PROPOSALS:
        # Chunk the proposal (simple fixed-size for this lab)
        text = proposal["text"]
        chunks = chunk_text(text, chunk_size=500, overlap=50)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{proposal['id']}-chunk-{i}"
            embedding = embed_text(chunk)
            index.upsert(
                vectors=[{
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "source": proposal["title"],
                        "category": proposal["category"],
                        "chunk_index": i,
                    },
                }],
                namespace=PROPOSALS_NAMESPACE,
            )
        print(f"  Ingested: {proposal['title']} ({len(chunks)} chunks)")

    print("\nIngesting company knowledge...")
    for doc in COMPANY_KNOWLEDGE:
        chunks = chunk_text(doc["text"], chunk_size=500, overlap=50)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['id']}-chunk-{i}"
            embedding = embed_text(chunk)
            index.upsert(
                vectors=[{
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "source": doc["title"],
                        "category": doc["category"],
                        "chunk_index": i,
                    },
                }],
                namespace=KNOWLEDGE_NAMESPACE,
            )
        print(f"  Ingested: {doc['title']} ({len(chunks)} chunks)")

    print("\nIngestion complete.")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Simple word-based chunking with overlap."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks


# ── Step E: Input Guard ───────────────────────────────────────────────────────

def input_guard(state: RFPPipelineState) -> dict:
    """
    Security: Sanitize the RFP input.
    - Check for injection patterns
    - Enforce length limits
    - Basic structural validation
    """
    trace = langfuse.trace(id=state["trace_id"], name="rfp-pipeline")
    span = trace.span(name="input-guard")

    rfp = state["rfp_text"]
    errors = list(state.get("errors", []))

    # Length check (RFPs can be long, but set a reasonable limit)
    if len(rfp) > 50000:
        rfp = rfp[:50000]
        errors.append("RFP text truncated to 50,000 characters")

    # Injection pattern filtering
    injection_patterns = [
        r"ignore\s+(previous|above|all)\s+(instructions|prompts)",
        r"you\s+are\s+now\s+",
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"OVERRIDE",
        r"bypass\s+(safety|security|guard)",
        r"forget\s+(everything|all|your)",
    ]

    sanitized = rfp
    for pattern in injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)
            errors.append(f"Injection pattern filtered in RFP: {pattern}")

    # Basic structure check: does this look like an RFP?
    rfp_indicators = ["proposal", "scope", "requirement", "vendor", "deadline", "budget"]
    indicator_count = sum(1 for ind in rfp_indicators if ind.lower() in sanitized.lower())

    if indicator_count < 2:
        errors.append(
            f"WARNING: Input has only {indicator_count}/6 RFP indicators. "
            f"This may not be a valid RFP document."
        )

    span.end(
        input={"rfp_length": len(rfp)},
        output={"sanitized_length": len(sanitized), "errors": errors},
    )

    return {
        "sanitized_rfp": sanitized,
        "errors": errors,
        "cumulative_cost": 0.0,
    }


# ── Step F: Agent 1 -- RFP Analyzer ──────────────────────────────────────────

def rfp_analyzer_agent(state: RFPPipelineState) -> dict:
    """
    Agent 1: RFP Analyzer
    - Reads the full RFP
    - Extracts structured requirements
    - Identifies which sections the response needs
    - Scores overall complexity (1-10)
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(
        name="rfp-analyzer",
        model=CLAUDE_MODEL,
        input={"rfp_length": len(state["sanitized_rfp"])},
    )

    system_prompt = """You are an expert RFP analyst at Acme Corporation, a B2B analytics company.
You analyze incoming RFPs to extract structured requirements and prepare your team
for response drafting.

Given an RFP document, extract:

1. requirements: A list of specific requirements, each with:
   - id: Short identifier (e.g., "REQ-01")
   - description: What is being asked for
   - category: One of [technical, experience, team, timeline, cost, compliance]
   - priority: HIGH (explicitly required), MEDIUM (strongly preferred), LOW (nice to have)
   - response_section: Which proposal section should address this

2. sections_needed: The list of sections the response must include
   (as specified in the RFP's "Proposal Format" or similar section)

3. complexity_score: 1-10 rating based on:
   - Number of requirements
   - Technical depth required
   - Integration complexity
   - Compliance requirements
   - Domain expertise needed

Return valid JSON with keys: requirements, sections_needed, complexity_score.
No text outside the JSON."""

    user_prompt = f"""Analyze this RFP and extract structured requirements:

{state['sanitized_rfp']}"""

    response = call_claude(system_prompt, user_prompt, max_tokens=2000)
    cumulative_cost = state.get("cumulative_cost", 0) + response["cost"]

    # Parse response
    try:
        parsed = json.loads(response["content"])
        requirements = parsed.get("requirements", [])
        sections_needed = parsed.get("sections_needed", [])
        complexity_score = parsed.get("complexity_score", 5)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response["content"], re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                requirements = parsed.get("requirements", [])
                sections_needed = parsed.get("sections_needed", [])
                complexity_score = parsed.get("complexity_score", 5)
            except json.JSONDecodeError:
                requirements = []
                sections_needed = [
                    "Technical Approach",
                    "Healthcare Experience",
                    "Team Qualifications",
                    "Timeline",
                    "Cost and Value",
                ]
                complexity_score = 5
        else:
            requirements = []
            sections_needed = [
                "Technical Approach",
                "Healthcare Experience",
                "Team Qualifications",
                "Timeline",
                "Cost and Value",
            ]
            complexity_score = 5

    generation.end(
        output={
            "requirements_count": len(requirements),
            "sections": sections_needed,
            "complexity": complexity_score,
        },
        usage={
            "input": response["input_tokens"],
            "output": response["output_tokens"],
        },
    )

    return {
        "requirements": requirements,
        "sections_needed": sections_needed,
        "complexity_score": complexity_score,
        "cumulative_cost": cumulative_cost,
        "metadata": {
            **state.get("metadata", {}),
            "rfp_analyzer": {
                "requirements_count": len(requirements),
                "complexity_score": complexity_score,
                "cost": response["cost"],
                "latency": response["latency"],
                "input_tokens": response["input_tokens"],
                "output_tokens": response["output_tokens"],
            },
        },
    }


# ── Step G: Agent 2 -- Knowledge Retriever ───────────────────────────────────

def knowledge_retriever_agent(state: RFPPipelineState) -> dict:
    """
    Agent 2: Knowledge Retriever (Agentic RAG)
    - For each section needed, determines the best search strategy
    - Routes queries to the appropriate Pinecone namespace
    - Performs iterative refinement if initial results are insufficient
    """
    trace = langfuse.trace(id=state["trace_id"])
    span = trace.span(name="knowledge-retriever")

    retrieved = {}
    retriever_metadata = {"sections": {}, "total_chunks_retrieved": 0}

    for section in state["sections_needed"]:
        section_span = span.span(name=f"retrieve-{section}")
        start_time = time.time()

        # Route to appropriate namespace based on section type
        if section.lower() in ["technical approach", "timeline"]:
            # Search both proposals and knowledge
            namespaces = [PROPOSALS_NAMESPACE, KNOWLEDGE_NAMESPACE]
        elif section.lower() in ["healthcare experience", "team qualifications"]:
            # Prioritize proposals for experience, knowledge for team
            namespaces = [PROPOSALS_NAMESPACE, KNOWLEDGE_NAMESPACE]
        elif section.lower() in ["cost and value"]:
            # Mostly knowledge base (rate cards, pricing models)
            namespaces = [KNOWLEDGE_NAMESPACE, PROPOSALS_NAMESPACE]
        else:
            namespaces = [PROPOSALS_NAMESPACE, KNOWLEDGE_NAMESPACE]

        # Build section-specific queries
        section_requirements = [
            r for r in state["requirements"]
            if r.get("response_section", "").lower() == section.lower()
        ]

        # Primary query: the section name + key requirements
        req_text = "; ".join([r["description"] for r in section_requirements[:3]])
        primary_query = f"{section}: {req_text}" if req_text else section

        # Search each namespace
        all_results = []
        seen_ids = set()

        for namespace in namespaces:
            results = search_pinecone(primary_query, namespace, top_k=5)
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

        # Iterative refinement: if fewer than 3 relevant results, refine query
        high_relevance = [r for r in all_results if r["score"] > 0.7]

        if len(high_relevance) < 3 and section_requirements:
            # Try a more specific query using the most important requirement
            refined_query = section_requirements[0]["description"]
            for namespace in namespaces:
                results = search_pinecone(refined_query, namespace, top_k=3)
                for r in results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_results.append(r)

        # Sort by relevance, keep top results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        all_results = all_results[:8]

        retrieved[section] = all_results
        elapsed = time.time() - start_time

        retriever_metadata["sections"][section] = {
            "chunks_retrieved": len(all_results),
            "namespaces_searched": namespaces,
            "refinement_needed": len(high_relevance) < 3,
            "latency": elapsed,
        }
        retriever_metadata["total_chunks_retrieved"] += len(all_results)

        section_span.end(
            output={
                "chunks": len(all_results),
                "top_score": all_results[0]["score"] if all_results else 0,
            },
        )

    span.end(
        output={
            "sections_retrieved": len(retrieved),
            "total_chunks": retriever_metadata["total_chunks_retrieved"],
        },
    )

    return {
        "retrieved_knowledge": retrieved,
        "metadata": {
            **state.get("metadata", {}),
            "knowledge_retriever": retriever_metadata,
        },
    }


# ── Step H: Agent 3 -- Response Drafter ──────────────────────────────────────

def response_drafter_agent(state: RFPPipelineState) -> dict:
    """
    Agent 3: Response Drafter
    - Generates each section of the RFP response
    - Uses retrieved knowledge as context
    - Incorporates revision feedback if this is a revision cycle
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(name="response-drafter", model=CLAUDE_MODEL)

    draft_sections = dict(state.get("draft_sections", {}))
    drafter_metadata = {"sections": {}}
    total_cost = 0.0

    # Determine which sections need drafting
    # On revision cycles, only redraft sections that scored below threshold
    if state.get("revision_count", 0) > 0 and state.get("quality_scores"):
        sections_to_draft = [
            section for section, scores in state["quality_scores"].items()
            if any(score < MIN_QUALITY_SCORE for score in scores.values())
        ]
    else:
        sections_to_draft = state["sections_needed"]

    for section in sections_to_draft:
        # Cost guard: check before each section
        current_cost = state.get("cumulative_cost", 0) + total_cost
        if current_cost >= MAX_COST_PER_RFP:
            draft_sections[section] = (
                f"[COST LIMIT REACHED: ${current_cost:.2f} / ${MAX_COST_PER_RFP:.2f}. "
                f"This section was not generated. Manual drafting required.]"
            )
            continue

        section_span = trace.span(name=f"draft-{section}")

        # Gather context for this section
        section_docs = state.get("retrieved_knowledge", {}).get(section, [])
        context_text = "\n\n---\n\n".join([
            f"[Source: {doc['source']}] (relevance: {doc['score']:.3f})\n{doc['text']}"
            for doc in section_docs
        ])

        # Gather relevant requirements
        section_reqs = [
            r for r in state.get("requirements", [])
            if r.get("response_section", "").lower() == section.lower()
        ]
        reqs_text = "\n".join([
            f"- [{r.get('priority', 'MEDIUM')}] {r['description']}"
            for r in section_reqs
        ])

        # Check for revision feedback
        feedback = state.get("revision_feedback", {}).get(section, "")
        previous_draft = draft_sections.get(section, "")

        revision_context = ""
        if feedback and previous_draft:
            revision_context = f"""
REVISION INSTRUCTIONS:
This is revision cycle {state.get('revision_count', 0)}.
Your previous draft scored below quality thresholds.

Previous draft:
{previous_draft}

Reviewer feedback:
{feedback}

Improve the draft based on this specific feedback. Do not start from scratch --
refine what you wrote before."""

        system_prompt = f"""You are a senior proposal writer at Acme Corporation, a B2B analytics company.
You are writing section "{section}" of a proposal response to Meridian Healthcare Systems.

Context about this RFP:
- Meridian is an existing $1.2M ACV customer using Product Alpha
- They operate 14 hospitals and 52 clinics, serving 2.3M patients
- They want AI-powered analytics enhancements
- Budget range: $800K - $1.2M

Writing guidelines:
- Be specific and concrete. Reference actual Acme capabilities and past work.
- Ground every claim in the retrieved knowledge. Do not invent capabilities,
  case studies, or team members.
- Address each requirement explicitly.
- Use professional proposal tone: confident but not boastful.
- Appropriate length: 300-500 words per section.
- Include brief citations where you reference past work (e.g., "as demonstrated
  in our Midwest Health Network engagement").
- If the retrieved knowledge does not contain relevant information for a claim,
  mark it with [REQUIRES HUMAN INPUT] rather than fabricating details."""

        user_prompt = f"""Write the "{section}" section of our RFP response.

REQUIREMENTS TO ADDRESS:
{reqs_text if reqs_text else "No specific requirements extracted for this section."}

RETRIEVED KNOWLEDGE AND PAST PROPOSALS:
{context_text if context_text else "No relevant documents retrieved for this section."}

{revision_context}

Write the section now."""

        response = call_claude(system_prompt, user_prompt, max_tokens=1200)
        total_cost += response["cost"]

        draft_sections[section] = response["content"]

        drafter_metadata["sections"][section] = {
            "word_count": len(response["content"].split()),
            "cost": response["cost"],
            "latency": response["latency"],
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "is_revision": state.get("revision_count", 0) > 0,
        }

        section_span.end(
            output={"word_count": len(response["content"].split())},
            input={"requirements_count": len(section_reqs)},
        )

    generation.end(
        output={
            "sections_drafted": len(sections_to_draft),
            "total_words": sum(
                len(v.split()) for v in draft_sections.values()
            ),
        },
    )

    return {
        "draft_sections": draft_sections,
        "cumulative_cost": state.get("cumulative_cost", 0) + total_cost,
        "metadata": {
            **state.get("metadata", {}),
            f"drafter_cycle_{state.get('revision_count', 0)}": drafter_metadata,
        },
    }


# ── Step I: Agent 4 -- Quality Reviewer ──────────────────────────────────────

def quality_reviewer_agent(state: RFPPipelineState) -> dict:
    """
    Agent 4: Quality Reviewer
    - Scores each drafted section on relevance, completeness, and accuracy (0-10)
    - Provides specific feedback for sections scoring below 7
    - Determines whether revision is needed
    """
    trace = langfuse.trace(id=state["trace_id"])
    generation = trace.generation(name="quality-reviewer", model=CLAUDE_MODEL)

    quality_scores = {}
    revision_feedback = {}
    reviewer_metadata = {"sections": {}}
    total_cost = 0.0

    for section, draft in state.get("draft_sections", {}).items():
        # Skip sections that hit the cost limit
        if "[COST LIMIT REACHED" in draft:
            quality_scores[section] = {"relevance": 0, "completeness": 0, "accuracy": 0}
            revision_feedback[section] = "Section was not generated due to cost limits."
            continue

        # Cost guard
        current_cost = state.get("cumulative_cost", 0) + total_cost
        if current_cost >= MAX_COST_PER_RFP:
            quality_scores[section] = {"relevance": 5, "completeness": 5, "accuracy": 5}
            continue

        section_span = trace.span(name=f"review-{section}")

        # Get relevant requirements for this section
        section_reqs = [
            r for r in state.get("requirements", [])
            if r.get("response_section", "").lower() == section.lower()
        ]
        reqs_text = "\n".join([
            f"- [{r.get('priority', 'MEDIUM')}] {r['description']}"
            for r in section_reqs
        ])

        # Get the retrieved knowledge for grounding check
        section_docs = state.get("retrieved_knowledge", {}).get(section, [])
        evidence_text = "\n".join([
            f"[{doc['source']}]: {doc['text'][:200]}..."
            for doc in section_docs[:5]
        ])

        system_prompt = """You are a senior quality reviewer for RFP responses at Acme Corporation.
You evaluate draft proposal sections for quality and provide specific, actionable feedback.

Score each dimension 0-10:
- relevance: Does the section address what the RFP asks for? Does it speak to the
  customer's specific situation (Meridian Healthcare, 14 hospitals, etc.)?
- completeness: Are all requirements for this section addressed? Are there gaps?
- accuracy: Are claims grounded in the provided evidence? Are there any statements
  that appear fabricated or unsupported?

Scoring guide:
- 9-10: Excellent, ready to submit
- 7-8: Good, minor improvements possible
- 5-6: Adequate but needs revision
- 3-4: Significant gaps or issues
- 1-2: Major problems, requires rewrite

If ANY score is below 7, provide specific feedback explaining:
1. What is wrong
2. What specific improvement is needed
3. What evidence should be incorporated

Return valid JSON: {"relevance": N, "completeness": N, "accuracy": N, "feedback": "..."}
If all scores are 7+, feedback can be empty string."""

        user_prompt = f"""Review this "{section}" section of our RFP response to Meridian Healthcare.

REQUIREMENTS THIS SECTION SHOULD ADDRESS:
{reqs_text if reqs_text else "No specific requirements extracted."}

AVAILABLE EVIDENCE (from past proposals and knowledge base):
{evidence_text if evidence_text else "No specific evidence available."}

DRAFT TO REVIEW:
{draft}

Score and provide feedback."""

        response = call_claude(system_prompt, user_prompt, max_tokens=600)
        total_cost += response["cost"]

        # Parse review
        try:
            review = json.loads(response["content"])
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response["content"], re.DOTALL)
            if json_match:
                try:
                    review = json.loads(json_match.group())
                except json.JSONDecodeError:
                    review = {"relevance": 6, "completeness": 6, "accuracy": 6,
                             "feedback": "Unable to parse reviewer output."}
            else:
                review = {"relevance": 6, "completeness": 6, "accuracy": 6,
                         "feedback": "Unable to parse reviewer output."}

        scores = {
            "relevance": review.get("relevance", 5),
            "completeness": review.get("completeness", 5),
            "accuracy": review.get("accuracy", 5),
        }
        quality_scores[section] = scores

        feedback = review.get("feedback", "")
        if feedback:
            revision_feedback[section] = feedback

        reviewer_metadata["sections"][section] = {
            "scores": scores,
            "needs_revision": any(s < MIN_QUALITY_SCORE for s in scores.values()),
            "cost": response["cost"],
            "latency": response["latency"],
        }

        section_span.end(
            output={"scores": scores, "has_feedback": bool(feedback)},
        )

    generation.end(
        output={
            "sections_reviewed": len(quality_scores),
            "sections_needing_revision": sum(
                1 for scores in quality_scores.values()
                if any(s < MIN_QUALITY_SCORE for s in scores.values())
            ),
        },
    )

    return {
        "quality_scores": quality_scores,
        "revision_feedback": revision_feedback,
        "cumulative_cost": state.get("cumulative_cost", 0) + total_cost,
        "metadata": {
            **state.get("metadata", {}),
            f"reviewer_cycle_{state.get('revision_count', 0)}": reviewer_metadata,
        },
    }


# ── Step J: LangGraph Wiring with Conditional Edges ──────────────────────────

def should_revise(state: RFPPipelineState) -> str:
    """
    Conditional edge: determine whether to revise or finalize.

    Routes to:
    - "response_drafter": if any section scores below 7 AND revision count < max
    - "output_guard": if all sections pass OR max revisions reached
    """
    revision_count = state.get("revision_count", 0)
    quality_scores = state.get("quality_scores", {})
    cumulative_cost = state.get("cumulative_cost", 0)

    # Hard limits
    if revision_count >= MAX_REVISION_CYCLES:
        print(f"  Max revision cycles ({MAX_REVISION_CYCLES}) reached. Finalizing.")
        return "output_guard"

    if cumulative_cost >= MAX_COST_PER_RFP:
        print(f"  Cost limit (${MAX_COST_PER_RFP}) reached. Finalizing.")
        return "output_guard"

    # Check if any section needs revision
    needs_revision = False
    for section, scores in quality_scores.items():
        if any(score < MIN_QUALITY_SCORE for score in scores.values()):
            needs_revision = True
            print(f"  Section '{section}' scored below {MIN_QUALITY_SCORE}: {scores}")

    if needs_revision:
        print(f"  Routing to revision cycle {revision_count + 1}...")
        return "increment_revision"
    else:
        print(f"  All sections pass quality threshold. Finalizing.")
        return "output_guard"


def increment_revision(state: RFPPipelineState) -> dict:
    """Increment the revision counter before re-entering the drafter."""
    return {
        "revision_count": state.get("revision_count", 0) + 1,
    }


def build_rfp_pipeline() -> StateGraph:
    """
    Build the RFP response pipeline with conditional revision loop.

    Flow:
    input_guard -> rfp_analyzer -> knowledge_retriever -> response_drafter
    -> quality_reviewer -> [revise or finalize] -> output_guard -> END
    """
    workflow = StateGraph(RFPPipelineState)

    # Add nodes
    workflow.add_node("input_guard", input_guard)
    workflow.add_node("rfp_analyzer", rfp_analyzer_agent)
    workflow.add_node("knowledge_retriever", knowledge_retriever_agent)
    workflow.add_node("response_drafter", response_drafter_agent)
    workflow.add_node("quality_reviewer", quality_reviewer_agent)
    workflow.add_node("increment_revision", increment_revision)
    workflow.add_node("output_guard", output_guard)

    # Linear edges for the main flow
    workflow.set_entry_point("input_guard")
    workflow.add_edge("input_guard", "rfp_analyzer")
    workflow.add_edge("rfp_analyzer", "knowledge_retriever")
    workflow.add_edge("knowledge_retriever", "response_drafter")
    workflow.add_edge("response_drafter", "quality_reviewer")

    # Conditional edge: revise or finalize
    workflow.add_conditional_edges(
        "quality_reviewer",
        should_revise,
        {
            "increment_revision": "increment_revision",
            "output_guard": "output_guard",
        },
    )

    # After incrementing revision count, go back to drafter
    workflow.add_edge("increment_revision", "response_drafter")

    # Final edge
    workflow.add_edge("output_guard", END)

    return workflow.compile()


# ── Step K: Output Guard ──────────────────────────────────────────────────────

def output_guard(state: RFPPipelineState) -> dict:
    """
    Final security and quality gate.
    - PII scan on all draft sections
    - Cost summary
    - Final formatting
    """
    trace = langfuse.trace(id=state["trace_id"])
    span = trace.span(name="output-guard")

    errors = list(state.get("errors", []))
    draft_sections = dict(state.get("draft_sections", {}))

    # PII scan each section
    total_pii_entities = 0
    for section, text in draft_sections.items():
        pii_results = pii_analyzer.analyze(
            text=text,
            language="en",
            entities=[
                "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
                "US_SSN", "US_PASSPORT", "IBAN_CODE", "PERSON",
            ],
        )

        # Only redact high-sensitivity PII (not person names, which are expected)
        sensitive_results = [
            r for r in pii_results
            if r.entity_type not in ["PERSON"]  # Names are expected in proposals
        ]

        if sensitive_results:
            anonymized = pii_anonymizer.anonymize(
                text=text,
                analyzer_results=sensitive_results,
            )
            draft_sections[section] = anonymized.text
            total_pii_entities += len(sensitive_results)
            errors.append(
                f"PII redacted in '{section}': {len(sensitive_results)} entities "
                f"({', '.join(set(r.entity_type for r in sensitive_results))})"
            )

    # Cost summary
    cumulative_cost = state.get("cumulative_cost", 0)
    metadata = dict(state.get("metadata", {}))
    metadata["final_summary"] = {
        "total_cost": cumulative_cost,
        "cost_limit": MAX_COST_PER_RFP,
        "cost_utilization": f"{(cumulative_cost / MAX_COST_PER_RFP) * 100:.1f}%",
        "revision_cycles": state.get("revision_count", 0),
        "pii_entities_redacted": total_pii_entities,
        "sections_generated": len(draft_sections),
    }

    span.end(
        output=metadata["final_summary"],
    )

    langfuse.flush()

    return {
        "draft_sections": draft_sections,
        "errors": errors,
        "metadata": metadata,
    }


# ── Step L: Main Runner ───────────────────────────────────────────────────────

def format_rfp_response(state: RFPPipelineState) -> str:
    """Format the final RFP response as a readable document."""
    lines = []
    lines.append("=" * 70)
    lines.append("  ACME CORPORATION")
    lines.append("  Proposal Response to Meridian Healthcare Systems")
    lines.append("  RFP-2024-MH-0847: AI-Powered Analytics Platform Enhancement")
    lines.append("=" * 70)
    lines.append("")

    for section in state.get("sections_needed", []):
        draft = state.get("draft_sections", {}).get(section, "[Section not generated]")
        scores = state.get("quality_scores", {}).get(section, {})

        lines.append(f"{'─' * 70}")
        lines.append(f"  {section.upper()}")
        if scores:
            score_str = " | ".join([f"{k}: {v}/10" for k, v in scores.items()])
            lines.append(f"  Quality Scores: {score_str}")
        lines.append(f"{'─' * 70}")
        lines.append("")
        lines.append(draft)
        lines.append("")

    return "\n".join(lines)


def run_rfp_pipeline(rfp_text: str = None) -> dict:
    """
    Execute the full RFP response pipeline.
    """
    if rfp_text is None:
        rfp_text = SAMPLE_RFP

    trace_id = f"capstone-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    initial_state: RFPPipelineState = {
        "rfp_text": rfp_text,
        "sanitized_rfp": "",
        "requirements": [],
        "sections_needed": [],
        "complexity_score": 0,
        "retrieved_knowledge": {},
        "draft_sections": {},
        "revision_feedback": {},
        "quality_scores": {},
        "revision_count": 0,
        "metadata": {},
        "errors": [],
        "trace_id": trace_id,
        "cumulative_cost": 0.0,
    }

    print(f"\n{'=' * 70}")
    print(f"  RFP RESPONSE GENERATOR")
    print(f"  Trace ID: {trace_id}")
    print(f"  Cost Limit: ${MAX_COST_PER_RFP:.2f}")
    print(f"  Max Revision Cycles: {MAX_REVISION_CYCLES}")
    print(f"{'=' * 70}\n")

    pipeline = build_rfp_pipeline()

    try:
        print("  [1/5] Input Guard: Sanitizing RFP...")
        print("  [2/5] RFP Analyzer: Extracting requirements...")
        print("  [3/5] Knowledge Retriever: Searching past proposals...")
        print("  [4/5] Response Drafter: Generating sections...")
        print("  [5/5] Quality Reviewer: Scoring and revising...")
        print()

        final_state = pipeline.invoke(initial_state)

    except Exception as e:
        print(f"\n  PIPELINE ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"errors": [str(e)], "trace_id": trace_id}

    # Print the formatted response
    response_doc = format_rfp_response(final_state)
    print(response_doc)

    # Print metrics
    metadata = final_state.get("metadata", {})
    summary = metadata.get("final_summary", {})

    print(f"\n{'=' * 70}")
    print(f"  PIPELINE METRICS")
    print(f"{'=' * 70}")
    print(f"  Total cost:             ${summary.get('total_cost', 0):.4f}")
    print(f"  Cost utilization:       {summary.get('cost_utilization', 'N/A')}")
    print(f"  Revision cycles:        {summary.get('revision_cycles', 0)}")
    print(f"  PII entities redacted:  {summary.get('pii_entities_redacted', 0)}")
    print(f"  Sections generated:     {summary.get('sections_generated', 0)}")

    # Per-agent breakdown
    print(f"\n  Per-Agent Costs:")
    analyzer_meta = metadata.get("rfp_analyzer", {})
    print(f"    RFP Analyzer:     ${analyzer_meta.get('cost', 0):.4f} "
          f"({analyzer_meta.get('latency', 0):.2f}s)")

    for cycle in range(summary.get("revision_cycles", 0) + 1):
        drafter_key = f"drafter_cycle_{cycle}"
        reviewer_key = f"reviewer_cycle_{cycle}"
        if drafter_key in metadata:
            drafter_cost = sum(
                s.get("cost", 0)
                for s in metadata[drafter_key].get("sections", {}).values()
            )
            print(f"    Drafter (cycle {cycle}):  ${drafter_cost:.4f}")
        if reviewer_key in metadata:
            reviewer_cost = sum(
                s.get("cost", 0)
                for s in metadata[reviewer_key].get("sections", {}).values()
            )
            print(f"    Reviewer (cycle {cycle}): ${reviewer_cost:.4f}")

    # Quality scores
    print(f"\n  Quality Scores:")
    for section, scores in final_state.get("quality_scores", {}).items():
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        status = "PASS" if all(s >= MIN_QUALITY_SCORE for s in scores.values()) else "NEEDS REVIEW"
        print(f"    {section:30s} avg: {avg_score:.1f}/10  [{status}]")

    if final_state.get("errors"):
        print(f"\n  Warnings/Errors:")
        for error in final_state["errors"]:
            print(f"    - {error}")

    print(f"\n  View full trace: {os.getenv('LANGFUSE_HOST')}/trace/{trace_id}")
    print(f"{'=' * 70}\n")

    return final_state


if __name__ == "__main__":
    import sys

    if "--ingest" in sys.argv:
        print("Running document ingestion...")
        ingest_documents()
    else:
        print("Running RFP pipeline...")
        print("(Run with --ingest first to populate Pinecone)")
        result = run_rfp_pipeline()
