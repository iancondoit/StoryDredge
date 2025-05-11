# Legacy StoryDredge Code (ARCHIVED)

⚠️ **WARNING: THIS CODE IS ARCHIVED AND SHOULD NOT BE USED OR MODIFIED** ⚠️

This directory contains the legacy codebase for StoryDredge that has been archived for reference purposes only. The code in this directory is no longer maintained and should not be used for new development.

## Why This Code Is Archived

The legacy codebase had several limitations:
- Complex and hard-to-maintain pipeline
- Slow processing due to API-based classification
- Limited article extraction capabilities
- Insufficient test coverage and error handling

## For New Development

Please use the modular architecture in the main `src/` directory. The new system provides:
- Clear separation of concerns with modular components
- Local LLM-based classification (no API costs or rate limits)
- Comprehensive test coverage
- Better performance and reliability

## Questions?

If you need to understand why something was implemented in a certain way in the legacy code, please consult the project maintainers rather than attempting to revive or modify this code. 