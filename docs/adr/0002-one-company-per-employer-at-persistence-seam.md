# One company per employer, enforced at the persistence seam

An employer holds at most one company. The domain `CompanyRegistry` encodes this rule, and `RedisCompanyRepository.save()` re-checks it against the persisted owner index, raising `CompanyError` when an owner would own a second (or a different) company. The bot's `/company` command is therefore a thin shell: it creates the entity, saves it, and surfaces the domain error to the user instead of duplicating its own check-then-create.

The rule lives at two reinforcing layers (domain invariant + repository guard) so it cannot drift: the bot enforces nothing it could get wrong, and a future non-bot write path would inherit the same guarantee from the repository.
