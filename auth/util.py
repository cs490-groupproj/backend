def can_access_client_endpoint(user, user_id, coach_client_list):
    if can_access_admin_endpoint(user):
        return True

    if user.user_id != user_id and user_id not in coach_client_list:
        return False

    return True

def can_access_admin_endpoint(user):
    if user.is_admin:
        return True
    return False