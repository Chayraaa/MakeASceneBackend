# Make A Scene – Backend Features

## User Management

* Registration / Login (Email & Password, OAuth)
* Role system: User, Moderator, Admin
* Age flag (over/under 18)
* Password reset
* Email confirmation
* Self-deletion
* Email preferences (opt-in/out)
* Store messages sent to the user

### User Tag Selection

* Users can save tags
* Users can search for tags
* Users can subscribe to site accounts
* Users can subscribe to events
* Users can block tags and site accounts

### User Feed

* “For You” feed based on:

  * User tags
  * Filters (datetime, location, include/exclude tags)
* Feed for newest events nearby (with filters)
* “Get Involved” feed:

  * Events in planning
  * Based on nearby activity
  * With filters

## Verification

* Initiative / artist name
* Description of activity
* External sources (e.g. website)
* Contact information (email, phone)
* Location
* Typical event type (e.g. concerts, movies)
* Site account name
* Additional information

## Moderation

* Moderation team can approve/deny user verification for site-account creation
* Moderation team can assign/change admin of a site account
* Moderation team can delete:

  * Users
  * Events
  * Site accounts

### Flow

* Moderation decision (approve/deny)
* If approved:

  * Send email notification
  * Create a site account
  * Grant access to user

## Site Account Management

* Can be created by verified users
* Can publish events
* Verified users can add other users as moderators
* Users can remove themselves from a site account
* Store default collaborators
* Can send messages to subscribers

## Event

* Location
* Date
* Tags
* NSFW flag
* Age restriction
* Name
* “Get Involved” flag (event in planning)
* Template support (images, text, etc.)
* Conflict check:

  * Ensure no overlapping events at the same time /place for a site account
* Collaboration:

  * Can include multiple site accounts
  * If not default collaborators → send a collaboration request
* Calendar event generation (e.g. ICS)
* Notifications:

  * Updates / changes
  * Messages to subscribers

## Filter

* Location
* Date
* Tags
* NSFW
* Age restriction

## Search Bar

* Tags
* Site accounts
* Event names
