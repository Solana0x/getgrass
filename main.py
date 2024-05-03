# -*- coding: utf-8 -*-
# @Author   :Solana0x
# @File     :main.py
# @Software :PyCharm
import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)
                send_ping_task = asyncio.create_task(send_ping())
                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(f"Error with proxy {socks5_proxy}: {str(e)}")
            if "[SSL: WRONG_VERSION_NUMBER]" in str(e) or "invalid length of packed IP address string" in str(e):
                logger.info(f"Removing error proxy from the list: {socks5_proxy}")
                remove_proxy_from_list(socks5_proxy)
                return None  # Return None to signal to the main loop to replace this proxy
            elif "" in str(e):
                logger.info(f"Removing error proxy from the list: {socks5_proxy}")
                remove_proxy_from_list(socks5_proxy)
                return None  # Return None to signal to the main loop to replace this 
            elif "Empty connect reply" in str(e) or "Device creation limit exceeded" in str(e):
                logger.info(f"Removing error proxy from the list: {socks5_proxy}")
                remove_proxy_from_list(socks5_proxy)
                return None  # Return None to signal to the main loop to replace this proxy
            elif "sent 1011 (internal error) keepalive ping timeout; no close frame received" in str(e):
                logger.info(f"Removing error proxy due to keepalive ping timeout: {socks5_proxy}")
                remove_proxy_from_list(socks5_proxy)
                return None  # Return None to signal to the main loop to replace this proxy
            else:
                continue  # Continue to try to reconnect or handle other errors
async def main():
    _user_id = 'Replace Your User ID HERE'   # Replace Your User ID HERE 
    proxy_file = '/path/to/file' # your Path to Proxy3.txt file 
    # formate => socks5://username:pass@ip:port
    with open(proxy_file, 'r') as file:
        all_proxies = file.read().splitlines()

    active_proxies = random.sample(all_proxies, 15) # write the number of proxy you wana use
    tasks = {asyncio.create_task(connect_to_wss(proxy, _user_id)): proxy for proxy in active_proxies}

    while True:
        done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.result() is None:
                failed_proxy = tasks[task]
                logger.info(f"Removing and replacing failed proxy: {failed_proxy}")
                active_proxies.remove(failed_proxy)
                new_proxy = random.choice(all_proxies)
                active_proxies.append(new_proxy)
                new_task = asyncio.create_task(connect_to_wss(new_proxy, _user_id))
                tasks[new_task] = new_proxy  # Replace the task in the dictionary
            tasks.pop(task)  # Remove the completed task whether it succeeded or failed
        # Replenish the tasks if any have completed
        for proxy in set(active_proxies) - set(tasks.values()):
            new_task = asyncio.create_task(connect_to_wss(proxy, _user_id))
            tasks[new_task] = proxy

def remove_proxy_from_list(proxy):
    with open("/path/to/file/proxy.txt", "r+") as file:
        lines = file.readlines()
        file.seek(0)
        for line in lines:
            if line.strip() != proxy:
                file.write(line)
        file.truncate()

if __name__ == '__main__':
    asyncio.run(main())
