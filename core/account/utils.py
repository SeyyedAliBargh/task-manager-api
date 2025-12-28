# making a path for profiles images
def profile_image_path(instans, file_name):
    return f"profile/{instans.user.id}/{file_name}"