import openai
import os
import logging
from typing import List, Dict, Any
from scripts.semantic_engine import semantic_engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for classification thresholds
CLASSIFICATION_THRESHOLDS = {
    "aligned_threshold": float(os.getenv("ALIGNED_THRESHOLD", "0.7")),  # similarity >= 0.7
    "weak_threshold": float(os.getenv("WEAK_THRESHOLD", "0.4"))         # similarity >= 0.4
}

def suggest_improvement(sentence, closest_controls_with_metadata):
    """Enhanced RAG-based improvement suggestions with rich context"""
    try:
        # Prepare enriched context
        context_parts = []
        citations = []
        
        for i, control_data in enumerate(closest_controls_with_metadata[:3], 1):
            control_text = control_data["text"]
            framework = control_data["framework"]
            control_id = control_data.get("control_id", "Unknown")
            section = control_data.get("section", "General")
            confidence = control_data.get("similarity_score", 0.0)
            
            context_parts.append(f"""
Control {i} [{framework} - {control_id}]:
Section: {section}
Confidence: {confidence:.2f}
Text: {control_text}
""")
            citations.append(f"{framework} - {control_id}")
        
        prompt = f"""
You are a cybersecurity compliance expert. Based on the following controls from established frameworks, provide a specific, actionable policy improvement for the given policy sentence.

ORIGINAL POLICY SENTENCE:
{sentence}

RELEVANT FRAMEWORK CONTROLS:
{chr(10).join(context_parts)}

INSTRUCTIONS:
1. Use ONLY the provided controls as your source of truth
2. Draft a compliant policy statement that addresses gaps in the original sentence
3. Be specific and actionable
4. Cite which control(s) you used: {', '.join(citations)}
5. If you cannot provide a confident improvement based on these controls, say "Insufficient framework guidance for specific improvement"

IMPROVED POLICY:
"""

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating suggestion: {e}")
        return "Unable to generate suggestion due to an error."

def generate_recommendations(policy_sentences):
    """Simplified recommendation generation using enhanced semantic engine"""
    
    if not hasattr(semantic_engine, 'index') or semantic_engine.index is None:
        logger.error("Semantic engine not properly initialized")
        return []
    
    recommendations = []
    
    for sentence in policy_sentences:
        # Use enhanced retrieval with metadata
        try:
            results_with_metadata = semantic_engine.retrieve_with_metadata(sentence, top_k=5)
            
            if not results_with_metadata:
                continue
                
            # Get the best match
            best_match = results_with_metadata[0]
            similarity_score = best_match["similarity_score"]
            
            # Classify based on similarity (using configurable thresholds)
            if similarity_score >= CLASSIFICATION_THRESHOLDS["aligned_threshold"]:
                status = "Aligned"
                priority = "Low"
            elif similarity_score >= CLASSIFICATION_THRESHOLDS["weak_threshold"]:
                status = "Weak"
                priority = "Medium"
            else:
                status = "Missing"
                priority = "High"
            
            # Generate suggestion for Missing or Weak matches
            suggestion = ""
            if status in ["Missing", "Weak"]:
                suggestion = suggest_improvement(sentence, results_with_metadata)
            
            recommendation = {
                "sentence": sentence,
                "closest_control": best_match["text"],
                "framework": best_match["framework"],
                "control_id": best_match.get("control_id", "Unknown"),
                "section": best_match.get("section", "General"),
                "distance": round(1 - similarity_score, 3),  # Convert to distance
                "similarity_score": round(similarity_score, 3),
                "status": status,
                "priority": priority,
                "suggested_improvement": suggestion
            }
            
            recommendations.append(recommendation)
            
        except Exception as e:
            logger.error(f"Error processing sentence '{sentence[:50]}...': {e}")
            continue
    
    return recommendations

def generate_executive_summary(recommendations):
    """Generate executive summary with enhanced insights"""
    
    total_findings = len(recommendations)
    if total_findings == 0:
        return "No policy findings to report."
    
    # Count by status
    status_counts = {"Aligned": 0, "Weak": 0, "Missing": 0}
    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    framework_counts = {}
    
    # Calculate average similarity by status
    status_similarities = {"Aligned": [], "Weak": [], "Missing": []}
    
    for rec in recommendations:
        status_counts[rec["status"]] += 1
        priority_counts[rec["priority"]] += 1
        status_similarities[rec["status"]].append(rec["similarity_score"])
        
        framework = rec["framework"]
        framework_counts[framework] = framework_counts.get(framework, 0) + 1
    
    # Calculate percentages
    aligned_pct = round((status_counts["Aligned"] / total_findings) * 100, 1)
    weak_pct = round((status_counts["Weak"] / total_findings) * 100, 1)
    missing_pct = round((status_counts["Missing"] / total_findings) * 100, 1)
    
    # Calculate average confidences
    avg_confidences = {}
    for status, similarities in status_similarities.items():
        if similarities:
            avg_confidences[status] = round(sum(similarities) / len(similarities), 2)
        else:
            avg_confidences[status] = 0.0
    
    # Top frameworks
    top_frameworks = sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    summary = f"""
EXECUTIVE SUMMARY

Policy Compliance Analysis Results:
• Total Policy Statements Analyzed: {total_findings}
• Aligned with Framework Controls: {status_counts['Aligned']} ({aligned_pct}%) - Avg Confidence: {avg_confidences['Aligned']}
• Weakly Aligned (Needs Improvement): {status_counts['Weak']} ({weak_pct}%) - Avg Confidence: {avg_confidences['Weak']}
• Missing/Non-compliant: {status_counts['Missing']} ({missing_pct}%) - Avg Confidence: {avg_confidences['Missing']}

Priority Distribution:
• High Priority Items: {priority_counts['High']}
• Medium Priority Items: {priority_counts['Medium']}
• Low Priority Items: {priority_counts['Low']}

Top Referenced Frameworks:
{chr(10).join([f"• {fw}: {count} matches" for fw, count in top_frameworks])}

RECOMMENDATIONS:
1. Address {priority_counts['High']} high-priority gaps immediately
2. Review and strengthen {status_counts['Weak']} weakly aligned policies
3. Focus on frameworks with highest gap counts for systematic improvement
4. Consider regular policy reviews to maintain compliance alignment

Note: Classification thresholds - Aligned: ≥{CLASSIFICATION_THRESHOLDS['aligned_threshold']}, Weak: ≥{CLASSIFICATION_THRESHOLDS['weak_threshold']}, Missing: <{CLASSIFICATION_THRESHOLDS['weak_threshold']}
"""
    
    return summary.strip()