import time
import logging
from PIL import Image
import io
from requests_oauthlib import OAuth2Session
import json
import pygame
import random
from requests.exceptions import ConnectionError, HTTPError
from time import sleep

class DigitalPhotoFrame:
    def __init__(self, auth_folder='../auth/', credentials_file='credentials.json', token_file='token.json', folder_id_file='folder-id.txt'):
        self.display_time = 30
        self.connection_attempts = 0
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('photoframe.log', mode='w'),
                logging.StreamHandler()
            ]
        )
        
        self.session = self._initialize_session(auth_folder, credentials_file, token_file, folder_id_file)
        
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.screen_width, self.screen_height = self.screen.get_size()
    
    def _initialize_session(self, auth_folder, credentials_file, token_file, folder_id_file):

        try:
            with open(auth_folder + folder_id_file, 'r') as f:
                self.folder_id = f.read().strip()

            with open(auth_folder + credentials_file, 'r') as f:
                self.credentials = json.load(f)['web']
                
            with open(auth_folder + token_file, 'r') as f:
                self.token = json.load(f)

            return OAuth2Session(
                self.credentials['client_id'],
                token=self.token,
                auto_refresh_url=self.credentials['token_uri'],
                auto_refresh_kwargs={
                    'client_id': self.credentials['client_id'],
                    'client_secret': self.credentials['client_secret']
                },
                token_updater=lambda token: self._save_token(token)
            )
        
        except Exception as e:
            logging.error(f'Error during initalization: {e}')
            raise
    
    def _save_token(self, token):
        token['refresh_token'] = self.token['refresh_token']
        with open('token.json', 'w') as f:
            json.dump(token, f)
        self.token = token

    def fetch_photos(self):
        all_photos = []
        next_page_token = None

        try:
            while True:
                query = f"'{self.folder_id}' in parents"
                
                params = {
                    'q': query,
                    'fields': 'nextPageToken, files(id, name)'
                }
                if next_page_token:
                    params['pageToken'] = next_page_token

                try:
                    response = self.session.get(
                        'https://www.googleapis.com/drive/v3/files',
                        params=params
                    )
                    response.raise_for_status()
                except HTTPError as e:
                    if e.response.status_code == 401:
                        logging.info("Token expired, refreshing...")
                        self.session.refresh_token(
                            self.credentials['token_uri'],
                            refresh_token=self.token['refresh_token']
                        )
                        response = self.session.get(
                            'https://www.googleapis.com/drive/v3/files',
                            params=params
                        )
                        response.raise_for_status()
                    else:
                        raise

                data = response.json()
                all_photos.extend(data.get('files', []))
                
                if not (next_page_token := data.get('nextPageToken')):
                    break

        except ConnectionError as conn_err:
            self.connection_attempts += 1
            if self.connection_attempts < 10:
                logging.error(f'Connection error: {conn_err}\nRetrying...')
                sleep(5)
            else:
                logging.error(f'Maximum connection attempts exceeded: {conn_err}')
                raise

        except Exception as err:
            logging.error(f'Error fetching photos: {err}')
            raise
        
        logging.info(f'Total photos fetched: {len(all_photos)}')
        return all_photos

    def display_photo(self, media_item):
        try:
            download_url = f"https://www.googleapis.com/drive/v3/files/{media_item['id']}?alt=media"
            
            try:
                response = self.session.get(download_url)
                response.raise_for_status()
            except HTTPError as e:
                if e.response.status_code == 401:
                    logging.info("Token expired, refreshing...")
                    self.session.refresh_token(
                        self.credentials['token_uri'],
                        refresh_token=self.token['refresh_token']
                    )
                    response = self.session.get(download_url)
                    response.raise_for_status()
                else:
                    raise
            
            image = Image.open(io.BytesIO(response.content))
            image = image.rotate(270, expand=True)
            logging.info(f'Image downloaded: {image.width}x{image.height}')
            
            image = image.resize((self.screen_width, int(image.height * self.screen_width / image.width)))
            
            crop_top = (image.height - self.screen_height) // 2
            image = image.crop((0, crop_top, self.screen_width, crop_top + self.screen_height))
            
            pygame_surface = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
            self.screen.blit(pygame_surface, (0, 0))
            pygame.display.update()

            time.sleep(self.display_time)
            
        except Exception as e:
            logging.error(f'Error displaying photo: {e}')
            sleep(1)
    
    def run(self):
        while True:
            try:
                media_items = self.fetch_photos()
                random.shuffle(media_items)
                
                for item in media_items:
                    self.display_photo(item)
                    
            except Exception as e:
                logging.error(f'Error in main loop: {e}')
                return

if __name__ == '__main__':
    photo_frame = DigitalPhotoFrame()
    photo_frame.run()