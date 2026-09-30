#include "keybow.h"
#include "serial.h"
#include "gadget-hid.h"
#include "lights.h"
#include "profiles.h"
#include "updater.h"

#include <bcm2835.h>
#include <signal.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

int running = 0;
int key_index = 0;

unsigned short last_state[NUM_KEYS];
keybow_key mapping_table[NUM_KEYS];

void signal_handler(int dummy) {
    running = 0;
}

keybow_key get_key(unsigned short index){
    return mapping_table[index];
}

void add_key(unsigned short gpio_bcm, unsigned short hid_code, unsigned short led_index){
    mapping_table[key_index].gpio_bcm = gpio_bcm;
    mapping_table[key_index].hid_code = hid_code;
    mapping_table[key_index].led_index = led_index;
    key_index += 1;
}

int initGPIO() {
    if (!bcm2835_init()){
        return 1;
    }
    int x = 0;
    for(x = 0; x < NUM_KEYS; x++){
        keybow_key key = get_key(x);
        bcm2835_gpio_fsel(key.gpio_bcm, BCM2835_GPIO_FSEL_INPT);
        bcm2835_gpio_set_pud(key.gpio_bcm, BCM2835_GPIO_PUD_UP);
    }
    return 0;
}

int updateKeys() {
    int x = 0;
    for(x = 0; x < NUM_KEYS; x++){
        keybow_key key = get_key(x);
        int state = bcm2835_gpio_lev(key.gpio_bcm) == 0;
        if(state != last_state[x]){
            luaHandleKey(x, state);            
        }
        last_state[x] = state;
    }
    return 0;
}

void resetKeyState(void) {
    for (int i = 0; i < NUM_KEYS; i++) last_state[i] = 0;
}

int main() {
    int ret;
    chdir(KEYBOW_HOME);
    int update_boot = access(".keybow-update/pending", F_OK) == 0;

    add_key(RPI_V2_GPIO_P1_11, 0x27, 3);
    add_key(RPI_V2_GPIO_P1_13, 0x37, 7);
    add_key(RPI_V2_GPIO_P1_16, 0x28, 11);
    add_key(RPI_V2_GPIO_P1_15, 0x1e, 2);
    add_key(RPI_V2_GPIO_P1_18, 0x1f, 6);
    add_key(RPI_V2_GPIO_P1_29, 0x20, 10);
    add_key(RPI_V2_GPIO_P1_31, 0x21, 1);
    add_key(RPI_V2_GPIO_P1_32, 0x22, 5);
    add_key(RPI_V2_GPIO_P1_33, 0x23, 9);
    add_key(RPI_V2_GPIO_P1_38, 0x24, 0);
    add_key(RPI_V2_GPIO_P1_36, 0x25, 4);
    add_key(RPI_V2_GPIO_P1_37, 0x26, 8);

    if (initGPIO() != 0) {
        return 1;
    }

    ret = initUSB();
    if (ret != 0) return 1;
    ret = initHID();
    if(ret != 0) {
        return 1;
    }

#ifdef KEYBOW_DEBUG
    printf("Initializing LUA\n");
#endif

    ret = initLUA();
    if (ret != 0){
        return ret;
    }

    resetKeyState();

#ifdef KEYBOW_DEBUG
    printf("Initializing Lights\n");
#endif
    initLights();
    read_png_file("default.png");

    serial_open();

    printf("Running...\n");
    running = 1;
    signal(SIGINT, signal_handler);

    if (luaCallSetup() != 0 || (update_boot && luaUsingFallback())) return 1;

    lights_start();

    time_t ready_after = time(NULL) + 5;
    int marked_ready = 0;

    while (running){
        profiles_poll();
        luaTick();
        updateKeys();
        update_poll_reboot();
        if (update_boot && !marked_ready && time(NULL) >= ready_after) {
            FILE *ready = fopen(".keybow-update/ready", "wb");
            if (ready) {
                if (fwrite("ready\n", 1, 6, ready) == 6 && !fflush(ready) && !fsync(fileno(ready)))
                    marked_ready = 1;
                fclose(ready);
            }
        }
        usleep(1000);
    }

    lights_stop();

    printf("Closing LUA\n");
    luaClose();
    printf("Cleanup USB\n");
    cleanupUSB();
    printf("Cleanup BCM2835\n");
    bcm2835_close();

    return 0;
}
