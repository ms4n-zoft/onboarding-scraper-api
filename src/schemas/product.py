"""Pydantic models defining the structured output schema."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    phone_number: Optional[str] = Field(
        default=None, description="Primary phone number for sales or inquiries, without country code"
    )
    country_code: Optional[str] = Field(
        default=None, description="Country code for phone number (e.g., +1)"
    )
    support_email: Optional[str] = Field(
        default=None, description="Official support or contact email"
    )
    address: Optional[str] = Field(
        default=None, description="Mailing address or headquarters address"
    )


class SocialProfile(BaseModel):
    platform: str = Field(description="Social network or community name")
    url: str = Field(description="Full https URL to the profile")


class SocialLinks(BaseModel):
    linkedin: Optional[str] = Field(
        default=None, description="LinkedIn company profile URL"
    )
    twitter: Optional[str] = Field(
        default=None, description="Twitter profile URL"
    )
    facebook: Optional[str] = Field(
        default=None, description="Facebook page URL"
    )


class GCCInfo(BaseModel):
    offices: Optional[str] = Field(
        default=None, description="GCC office locations of the product or company"
    )
    customers: Optional[str] = Field(
        default=None, description="Major customers using the product in the Middle East"
    )
    local_address: Optional[str] = Field(
        default=None, description="Local address of the product/company in the GCC region"
    )
    arabic_available: Optional[bool] = Field(
        default=None, description="Indicates if the product is available in Arabic"
    )


class AICapabilityInfo(BaseModel):
    ai_usage_summary: Optional[str] = Field(
        default=None, description="Summary of where and how the product uses AI"
    )
    ai_technologies_used: Optional[str] = Field(
        default=None, description="AI technologies used such as GPT, Claude or proprietary models"
    )


class Web3Info(BaseModel):
    web3_company_status: Optional[str] = Field(
        default=None, description="Indicates whether the company/product is a Web3 company"
    )
    web3_components_list: Optional[str] = Field(
        default=None, description="Description of Web3 components or blockchain-related features"
    )


class Feature(BaseModel):
    name: str = Field(description="Feature name")
    description: Optional[str] = Field(
        default=None, description="Brief description of the feature"
    )


class PricingPlan(BaseModel):
    plan: str = Field(description="Pricing tier name (e.g., Free, Essentials, Premium)")
    entity: Optional[str] = Field(
        default=None, description="Billing entity (e.g., User, Contact, Project)"
    )
    amount: Optional[str] = Field(
        default=None, description="Price amount as string"
    )
    currency: Optional[str] = Field(
        default=None, description="Currency code (e.g., USD, EUR)"
    )
    period: Optional[str] = Field(
        default=None, description="Billing period (e.g., Month, Year)"
    )
    description: List[str] = Field(
        default_factory=list, description="List of features/details included in this plan"
    )
    is_free: Optional[bool] = Field(
        default=None, description="Whether this is a free plan"
    )


class DeploymentOption(BaseModel):
    type: str = Field(description="Deployment type (e.g., Cloud, On-Premise, Web-Based)")


class SupportOption(BaseModel):
    type: str = Field(description="Support type (e.g., Email, Chat, Phone, Knowledge Base)")


class CompanyInfo(BaseModel):
    overview: Optional[str] = Field(
        default=None, description="Company overview and background"
    )
    founding: Optional[str] = Field(
        default=None,
        description="Founding story, key founder names, and early company history",
    )
    funding_info: Optional[str] = Field(
        default=None, description="Investment rounds and major investors"
    )
    acquisitions: Optional[str] = Field(
        default=None, description="Major acquisitions and product expansions"
    )
    global_presence: Optional[str] = Field(
        default=None, description="Global presence details, typically included as part of community and growth narrative",
    )
    company_culture: Optional[str] = Field(
        default=None, description="Company culture, values, and work environment"
    )
    community: Optional[str] = Field(
        default=None, description="User communities, forums, and online presence"
    )
    growth_story: Optional[str] = Field(
        default=None, description="Narrative describing the company’s growth trajectory"
    )
    valuation: Optional[str] = Field(
        default=None, description="Company valuation if available"
    )
    product_expansion: Optional[str] = Field(
        default=None, description="Details about global or regional expansion of product offerings"
    )
    recent_new_features: Optional[str] = Field(
        default=None, description="Major new features added to the product recently"
    )
    product_offerings: List[str] = Field(
        default_factory=list,
        description="List of key product offerings, modules, or SKUs",
    )


class ReviewSummary(BaseModel):
    strengths: List[str] = Field(
        default_factory=list,
        description="Common positive sentiments from review platforms",
    )
    strengths_paragraph: Optional[str] = Field(
        default=None, description="Paragraph summary of positive reviews"
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Repeated concerns or drawbacks from reviews",
    )
    weaknesses_paragraph: Optional[str] = Field(
        default=None, description="Paragraph summary of negative reviews"
    )
    overall_rating: Optional[float] = Field(
        default=None, description="Weighted average rating from major review platforms"
    )
    review_sources: List[str] = Field(
        default_factory=list,
        description="Sources used for ratings (e.g., G2, Capterra, GetApp)",
    )



class ImplementationFAQ(BaseModel):
    implementation: Optional[str] = Field(
        default=None,
        description="Implementation process and typical time required for onboarding and go-live",
    )
    customization: Optional[str] = Field(
        default=None, description="Customization capabilities and available options"
    )
    training: Optional[str] = Field(
        default=None, description="Types of training offered (webinars, documentation, live)"
    )
    security_measures: Optional[str] = Field(
        default=None, description="Security measures (SSL, encryption, ISO certifications, etc.)"
    )
    update: Optional[str] = Field(
        default=None,
        description="Recent product updates and typical update frequency or release cadence",
    )
    data_ownership: Optional[str] = Field(
        default=None, description="Data ownership policy and export options"
    )
    scaling: Optional[str] = Field(
        default=None, description="How the product scales with team size and organizational growth"
    )
    terms_and_conditions_url: Optional[str] = Field(
        default=None, description="Direct URL to terms and conditions document"
    )
    compliance_standards: List[str] = Field(
        default_factory=list,
        description="Compliance certifications (GDPR, HIPAA, SOC 2, ISO, etc.)",
    )
    additional_costs: Optional[str] = Field(
        default=None, description="Setup fees, maintenance costs, or support charges"
    )
    cancellation_terms: Optional[str] = Field(
        default=None, description="Cancellation policy terms from FAQ"
    )
    contract_renewal_terms: Optional[str] = Field(
        default=None, description="Contract renewal and cancellation terms"
    )


# Note: MetaKeysInfo removed per spec cleanup (not part of official schema)


class Integration(BaseModel):
    name: str = Field(description="Integration partner name")
    website: Optional[str] = Field(
        default=None, description="Partner website URL"
    )
    logo: Optional[str] = Field(
        default=None, description="Partner logo URL"
    )


class PricingInfo(BaseModel):
    overview: Optional[str] = Field(
        default=None, description="General pricing strategy and overview (e.g., free trial, freemium, tiered plans)"
    )
    pricing_url: Optional[str] = Field(
        default=None, description="Direct link to pricing page"
    )
    pricing_plans: List[PricingPlan] = Field(
        default_factory=list, description="Detailed pricing tiers with plan details"
    )


class ProductSnapshot(BaseModel):
    # Basic Product Information
    product_name: Optional[str] = Field(
        default=None, description="Official product name"
    )
    company_name: Optional[str] = Field(
        default=None, description="Parent or developer company name"
    )
    website: Optional[str] = Field(
        default=None, description="Official product or company website (https://)"
    )
    company_website: Optional[str] = Field(
        default=None, description="Official parent company website (if different from product website)"
    )
    weburl: Optional[str] = Field(
        default=None, description="Internal slug for the product page; must use only lowercase letters and hyphens"
    )

    # Product Descriptions (as per data team spec)
    short_description: Optional[str] = Field(
        default=None,
        description="Short 1-2 sentence product description for the product details page",
    )
    elevator_pitch: Optional[str] = Field(
        default=None,
        description="Full elevator pitch and detailed overview of the product (500-700 words)",
    )
    competitive_advantage: Optional[str] = Field(
        default=None,
        description="Competitive edge and how the product differs from alternatives (300-500 words)",
    )

    # Company & Founding Information
    year_founded: Optional[int] = Field(
        default=None, description="Year the company or product was founded"
    )
    hq_location: Optional[str] = Field(
        default=None, description="City, Country - headquarters location"
    )

    # Categorization
    industry: List[str] = Field(
        default_factory=list,
        description="Applicable vertical(s) (e.g., Finance, Accounting)",
    )
    market_size: Optional[str] = Field(
        default=None,
        description="Primary market segment or company size served (e.g., SMB, Mid-Market, Enterprise)",
    )
    parent_category: Optional[str] = Field(
        default=None, description="Primary software category"
    )
    sub_category: Optional[str] = Field(
        default=None, description="Niche category"
    )

    # Contact & Social Information
    contact: ContactInfo = Field(default_factory=ContactInfo)
    social_profiles: Optional[SocialLinks] = Field(
        default=None, description="Structured social media links (LinkedIn, Twitter, Facebook)"
    )

    # Product Features
    feature_overview: Optional[str] = Field(
        default=None, description="Short narrative summary of key product features (up to ~200 words)"
    )
    features: List[Feature] = Field(
        default_factory=list, description="Top 20 key product features and capabilities"
    )
    deployment_options: List[DeploymentOption] = Field(
        default_factory=list,
        description="Deployment options (Cloud, On-Premise, Web-Based, etc.)",
    )
    support_options: List[SupportOption] = Field(
        default_factory=list,
        description="Support channels (Email, Chat, Phone, Knowledge Base, etc.)",
    )

    # Pricing Information
    pricing: PricingInfo = Field(default_factory=PricingInfo)
    pricing_overview: Optional[str] = Field(
        default=None, description="Narrative overview of pricing strategy and structure (around 200 words)"
    )

    # FAQ & Implementation Details
    faq: ImplementationFAQ = Field(default_factory=ImplementationFAQ)

    # Company Information
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)

    # Reviews & Ratings
    reviews: ReviewSummary = Field(default_factory=ReviewSummary)

    # Additional Information
    languages_supported: List[str] = Field(
        default_factory=list, description="Supported product languages"
    )
    ai_capabilities: Optional[str] = Field(
        default=None, description="AI capabilities and where AI is used in the product"
    )
    gcc_availability: Optional[str] = Field(
        default=None, description="Free-text summary of GCC availability, offices, and local presence"
    )
    gcc_info: Optional[GCCInfo] = Field(
        default=None, description="Structured GCC availability and presence information"
    )
    ai_info: Optional[AICapabilityInfo] = Field(
        default=None, description="Structured AI capability information"
    )
    web3_info: Optional[Web3Info] = Field(
        default=None, description="Structured Web3-related information"
    )
    web3_components: Optional[str] = Field(
        default=None, description="Narrative description of any Web3 components or blockchain-related features"
    )

    technology_stack: List[str] = Field(
        default_factory=list, description="List of underlying technologies used by the product"
    )

    # Media & Visual Information
    logo_url: Optional[str] = Field(
        default=None, description="Official company/product logo URL (https://). Scraped from official website or company resources."
    )

    # Integration Information
    integrations: List[Integration] = Field(
        default_factory=list, description="Third-party integrations and partners"
    )