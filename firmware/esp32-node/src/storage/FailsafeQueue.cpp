#include "FailsafeQueue.h"

bool FailsafeQueue::push(const String& payload) {
  if (queue_.size() >= kMaxQueue) {
    queue_.erase(queue_.begin());
  }
  queue_.push_back(payload);
  return true;
}

bool FailsafeQueue::pop(String& payload) {
  if (queue_.empty()) return false;
  payload = queue_.front();
  queue_.erase(queue_.begin());
  return true;
}
