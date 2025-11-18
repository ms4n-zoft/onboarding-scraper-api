"""Pydantic models defining the structured output schema."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    phone_number: Optional[str] = Field(
        default=None, description="Primary phone number for sales or inquiries"
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
    founding_story: Optional[str] = Field(
        default=None, description="Origin story and founding details"
    )
    founder_names: List[str] = Field(
        default_factory=list, description="Names of company founders"
    )
    funding_info: Optional[str] = Field(
        default=None, description="Investment rounds and major investors"
    )
    acquisitions: Optional[str] = Field(
        default=None, description="Major acquisitions and product expansions"
    )
    global_presence: List[str] = Field(
        default_factory=list, description="Geographic regions and offices"
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


class RatingsBreakdown(BaseModel):
    overall_rating: Optional[float] = Field(
        default=None, description="Overall rating score"
    )
    ease_of_use: Optional[float] = Field(
        default=None, description="Ease of use rating"
    )
    breadth_of_features: Optional[float] = Field(
        default=None, description="Feature breadth rating"
    )
    ease_of_implementation: Optional[float] = Field(
        default=None, description="Implementation ease rating"
    )
    value_for_money: Optional[float] = Field(
        default=None, description="Value for money rating"
    )
    customer_support: Optional[float] = Field(
        default=None, description="Customer support rating"
    )
    total_reviews: Optional[int] = Field(
        default=None, description="Total number of reviews aggregated"
    )


class ImplementationFAQ(BaseModel):
    implementation_process: Optional[str] = Field(
        default=None, description="Step-by-step onboarding and implementation process"
    )
    implementation_time: Optional[str] = Field(
        default=None, description="Typical time required for implementation"
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
    update_frequency: Optional[str] = Field(
        default=None, description="Product update frequency and management"
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


class MetaKeysInfo(BaseModel):
    description: Optional[str] = Field(
        default=None, description="Meta description for SEO"
    )
    title: Optional[str] = Field(
        default=None, description="Meta title for SEO"
    )
    h1: Optional[str] = Field(
        default=None, description="H1 heading text"
    )
    header: Optional[str] = Field(
        default=None, description="Header text"
    )


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
        default=None, description="General pricing strategy and overview (200 words)"
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
        default=None, description="Official company website (https://)"
    )
    weburl: Optional[str] = Field(
        default=None, description="URL slug for the product page"
    )

    # Product Descriptions
    description: Optional[str] = Field(
        default=None,
        description="Short product description (1-2 sentences)",
    )
    short_description_1_2_lines: Optional[str] = Field(
        default=None, description="One to two line summary of the product"
    )
    product_description_short: Optional[str] = Field(
        default=None,
        description="SEO-optimized meta description, 120-160 words",
    )
    meta_description: Optional[str] = Field(
        default=None, description="SEO-optimized meta description (120-160 words)"
    )
    overview: Optional[str] = Field(
        default=None,
        description="What the tool does (2-3 paragraphs)",
    )
    elevator_pitch: Optional[str] = Field(
        default=None,
        description="Full overview of product, 500-700 words",
    )
    competitive_advantage: Optional[str] = Field(
        default=None,
        description="Unique selling proposition and competitive edge (300-500 words)",
    )
    usp: Optional[str] = Field(
        default=None, description="Unique selling proposition summary"
    )

    # Company & Founding Information
    founding_year: Optional[int] = Field(
        default=None, description="Year product or company was founded"
    )
    year_founded: Optional[int] = Field(
        default=None, description="Year company was founded (alternate field)"
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
        description="Primary market segment (SMB, Mid-Market, Enterprise)",
    )
    industry_size: List[str] = Field(
        default_factory=list,
        description="Industry size segments (e.g., All Segment, SMB, Enterprise)",
    )
    industry_size_single: Optional[str] = Field(
        default=None, description="Primary industry size classification (e.g., SMB, Enterprise)"
    )
    parent_category: Optional[str] = Field(
        default=None, description="Primary software category"
    )
    sub_category: Optional[str] = Field(
        default=None, description="Niche category"
    )

    # Contact & Social Information
    contact: ContactInfo = Field(default_factory=ContactInfo)
    social_links: List[SocialProfile] = Field(default_factory=list)
    social_profiles: Optional[SocialLinks] = Field(
        default=None, description="Structured social media links"
    )

    # Product Features
    feature_overview: Optional[str] = Field(
        default=None, description="1-2 line summary of features (200 words)"
    )
    features: List[Feature] = Field(
        default_factory=list, description="Top 20 key features and capabilities"
    )
    other_features: List[str] = Field(
        default_factory=list, description="Additional feature names/descriptions"
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
        default=None, description="General pricing strategy overview (200 words)"
    )
    pricing_details_web_url: Optional[str] = Field(
        default=None, description="URL to detailed pricing information"
    )

    # FAQ & Implementation Details
    faq: ImplementationFAQ = Field(default_factory=ImplementationFAQ)

    # Company Information
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)

    # Reviews & Ratings
    reviews: ReviewSummary = Field(default_factory=ReviewSummary)
    reviews_strengths: List[str] = Field(
        default_factory=list, description="Review strengths aggregated from platforms"
    )
    reviews_weakness: List[str] = Field(
        default_factory=list, description="Review weaknesses aggregated from platforms"
    )
    ratings: Optional[RatingsBreakdown] = Field(
        default=None, description="Detailed ratings breakdown"
    )

    # Additional Information
    languages_supported: List[str] = Field(
        default_factory=list, description="Supported product languages"
    )
    ai_capabilities: Optional[str] = Field(
        default=None, description="AI capabilities and where AI is used in the product"
    )
    ai_questions: Optional[str] = Field(
        default=None, description="AI-related questions and answers (HTML formatted)"
    )
    gcc_availability: Optional[str] = Field(
        default=None, description="GCC region availability and local presence"
    )
    gcc_info: Optional[GCCInfo] = Field(
        default=None, description="Structured GCC availability and presence information"
    )
    ai_info: Optional[AICapabilityInfo] = Field(
        default=None, description="Structured AI capability information"
    )
    gcp_availability: Optional[str] = Field(
        default=None, description="GCP region availability (alternate field, HTML formatted)"
    )
    web3_info: Optional[Web3Info] = Field(
        default=None, description="Structured Web3-related information"
    )
    web3_components: Optional[str] = Field(
        default=None, description="Web3 components or blockchain-related features"
    )
    web3_questions: Optional[str] = Field(
        default=None, description="Web3-related questions and answers (HTML formatted)"
    )

    technology_stack: List[str] = Field(
        default_factory=list, description="List of underlying technologies used by the product"
    )

    # Media & Visual Information
    logo_url: Optional[str] = Field(
        default=None, description="Official company/product logo URL (https://). Scraped from official website or company resources."
    )
    videos: List[str] = Field(
        default_factory=list, description="Video URLs (YouTube, Vimeo, etc.)"
    )

    # Integration Information
    integrations: List[Integration] = Field(
        default_factory=list, description="Third-party integrations and partners"
    )

    # SEO & Metadata
    meta_keys: Optional[MetaKeysInfo] = Field(
        default=None, description="SEO metadata (title, description, h1, etc.)"
    )
