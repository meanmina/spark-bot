class Poll:
  '''Stores all info for a poll and we can have multiple instances of it.'''
  room = None
  title = None
  description = None
  options = []
  votes = []
  closed = False

  def __init__(self, title, options, room):
    self.title = title
    self.options = options
    self.room = room
    self.votes = [0 for x in options]

  def set_votes(self, votes):
    if len(votes) != len(self.votes):
      return False
    self.votes = votes
    return True