def can_access_client_endpoint(auth_user, user_id, coach_client_list):
    if auth_user.user_id != user_id and user_id not in coach_client_list:
        return False
    return True