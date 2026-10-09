# MaaS Token Plan

MaaS Token Plan is a subscription service designed specifically for developers. After purchasing a plan, you can quickly integrate with mainstream AI tools and accelerate your development workflow.

## 1. Token Plan Advantages

- **Flexible switching among multiple code models**: With a single subscription, you can freely switch between the latest versions of GLM-5, GLM-5.1, Kimi-K2.6, DeepSeek-V3.2, and DeepSeek-V4-Flash models as needed
- **Compatible with mainstream AI tools**: Supports mainstream AI tools such as Claude Code and OpenClaw, with multiple tools sharing the plan quota, adapting to different development scenarios
- **Exceptional cost-effectiveness**: Significant discounts compared to API call pricing
- **Multiple plans for different scenarios**: Offers Lite, Standard, Pro, and Max plans to suit both regular and intensive programming scenarios
- **Stable performance**: The platform has multi-tenant isolation capabilities, so even during peak call periods there is no noticeable slowdown

## 2. Applicable Scenarios

Token Plan is suitable for individual development scenarios, helping developers complete coding tasks such as personal projects, learning and practice, and tool setup.

If you have enterprise-level development needs, please use MaaS API to call model services.

## 3. Constraints and Limitations

- Token Plan is only supported in the "西南-贵阳一" region
- Currently, MaaS Token Plan is primarily aimed at individual developers; enterprise users cannot purchase Token Plan at this time
- The same subscription plan can be used across all supported tools, with shared quota
- **Plan quota only takes effect within AI tools and cannot be used for API calls**. Using the dedicated Base URL and API Key associated with MaaS Token Plan benefits outside of AI tools may be identified as abuse or violation, resulting in subscription suspension or account ban
- You must use the models supported by Token Plan and the dedicated Base URL

## 4. Plan Details

| Model Name | Plan | Applicable Scenario | Usage Limit |
|----------|------|----------|----------|
| GLM-5, GLM-5.1, Kimi-K2.6 | Lite | Suitable for first-time experience with AI programming | Per subscription month: 50 million Tokens |
| GLM-5, GLM-5.1, Kimi-K2.6, DeepSeek-V3.2, DeepSeek-V4-Flash | Standard | Suitable for daily office work and light development | Per subscription month: 130 million Tokens |
| GLM-5, GLM-5.1, Kimi-K2.6, DeepSeek-V3.2, DeepSeek-V4-Flash | Pro | Suitable for developers and efficiency enthusiasts who use AI frequently every day | Per subscription month: 380 million Tokens |
| GLM-5, GLM-5.1, Kimi-K2.6, DeepSeek-V3.2, DeepSeek-V4-Flash | Max | Suitable for heavy users who treat AI as a core productivity tool | Per subscription month: 880 million Tokens |

> For specific pricing, please refer to the MaaS console and purchase page.

## 5. Key Parameters for Tool Integration

| Key Parameter | Description |
|----------|------|
| Model Name | Specify the Model Name in the tool configuration file to switch models in real time. Supported: GLM-5, GLM-5.1, Kimi-K2.6, DeepSeek-V3.2, DeepSeek-V4-Flash (lowercase format is supported) |
| Base Url | For tools compatible with OpenAI interface protocol: `https://api.modelarts-maas.com/plan/v2/chat/completions`; for tools compatible with Anthropic interface protocol: `https://api.modelarts-maas.com/plan/anthropic/v1/messages`. **If you do not use the specified dedicated Base URL, you will not be able to use Token Plan quota and may incur additional API request charges.** |
| API Key | Manage API Key |

## 6. Purchase Process

1. Log in to the MaaS console and select the "西南-贵阳一" region from the top navigation bar
2. In the left navigation bar, select "Management & Statistics > Subscription Management"
3. On the "Token Plan" page, click "Purchase" on the target plan card
4. On the "Purchase Token Plan" page, carefully read the purchase instructions, select the plan specifications, auto-renewal, etc. as needed, check "I have read and agree to the MaaS Model-as-a-Service Token Plan Activity Rules", review the configuration cost, and click "Purchase Now"
5. On the "Purchase Token Plan" page, review the order, select a payment method, and click "Confirm Payment"

> Token Plan is sold in limited quantities daily and can be purchased as needed during the sales start period. When the sales period ends or the plan is sold out, no further purchases can be made that day.

## 7. Plan Change Rules

- Subscription plans only support upgrades, not downgrades
- If the plan validity period ends and the plan quota is not exhausted, the remaining quota cannot continue to be used
- Upgrade cost = (New plan cost - Old plan cost) ÷ Plan cycle × Remaining cycle
- Upgraded plan token usage = New plan usage limit - Old plan already used amount

## 8. Common Questions

**Q: Do I need to separately activate model services after purchasing Token Plan?**
A: No. After purchasing a Token Plan, you can configure the Token Plan dedicated URL in various Coding and Agent tools and use the model services included in the plan.

**Q: Will other resource packs or account balance be consumed after the plan quota is exhausted?**
A: If the plan quota is exhausted within the time cycle and the plan is not upgraded or renewed, Token Plan does not support continued usage.

**Q: Can I use the Token Plan in multiple tools at the same time?**
A: Yes, you can use the same plan across all supported tools, but the quota is shared, and usage from all tools consumes the same plan quota.

**Q: Can I get a refund after subscribing to a plan?**
A: Once a subscription service is purchased, it is considered confirmed and non-refundable. We recommend selecting an appropriate subscription plan and cycle based on your usage needs.

**Q: Does Token Plan support team usage?**
A: Currently, MaaS Token Plan is primarily aimed at individual developers. For team collaboration, please use MaaS API pay-per-use billing.
