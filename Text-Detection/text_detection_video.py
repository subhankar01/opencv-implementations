# import the necessary packages
from imutils.object_detection import non_max_suppression
from imutils.video import VideoStream
from imutils.video import FPS
import imutils
import numpy as np 
import argparse
import time
import cv2


# function for decoding predictions
def decode_predictions(scores, geomery):
    # grab the number of rows and columns from the score volume
    # then initialise our set of bounding box rectangles and
    # corresponding confidence scores
    (numRows, numCols) = scores.shape[2:4]
    rects = []
    confidences = []
    for y in range(0, numRows):
        # extract the scores, followed by the geometrical data
        # used to derive potential bounding box coordinates that
        # surround text
        scoresData = scores[0, 0, y]
        xData0 = geometry[0, 0, y]
        xData1 = geometry[0, 1, y]
        xData2 = geometry[0, 2, y]
        xData3 = geometry[0, 3, y]
        anglesData = geometry[0, 4, y]

        # loop over the no.of columns
        for x in range(0, numCols):
            # if our score does not have sufficient probability, ignore it
            if scoresData[x] < args["min_confidence"]:
                continue
            
            # compute the offset factor as our resulting feature maps will be 4x smaller
            # than input image
            (offsetX, offsetY) = (x * 4.0, y * 4.0)

            # extract the rotation angle for the prediction and compute the sine and cosine
            angle = anglesData[x]
            cos = np.cos(angle)
            sin = np.sin(angle)

            # use the geometry volume to derive the width and height of the bounding box
            h = xData0[x] + xData2[x]
            w = xData1[x] + xData3[x]

            # compute both the starting and ending (x, y) coordinates for the
            # text prediction bounding box
            endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
            endY = int(offsetY + (sin * xData1[x]) + (cos * xData2[x]))
            startX = int(endX - w)
            startY = int(endY - h)

            # add the bounding box coordinates and probability score to our 
            # respective lists
            rects.append((startX, startY, endX, endY))
            confidences.append(scoresData[x])
    
    # return a tuple of bounding boxes and associated confidences
    return (rects, confidences)

# construct the argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", type=str, help = "path to optional input video file")
ap.add_argument("-east", "--east", type = str, help = "path to input EAST text detection")
ap.add_argument("-c", "--min-confidence", type=float, default = 0.5, help = "minimum probability required to inspect a region")
ap.add_argument("-w", "--width", type=int, default = 320, help = "resized image width(should be mulitple of 32)")
ap.add_argument("-e", "--height", type=int, default = 320, help = "resized image height(should be mulitple of 32)")
args = vars(ap.parse_args())

# initialise the original frame dimensions, new frame dimensions and
# ratio between the dimensions
(W, H) = (None, None)
(newW, newH) = (args["width"], args["height"])
(rW, rH) = (None, None)

# define the two output layer names for the EAST detector model
# first is the output probabilities and the second can be used to 
# derive bounding box coordinates of text
layerNames = [
    "feature_fusion/Conv_7/Sigmoid",
    "feature_fusion/concat_3"]

# load the pre-trained EAST text detector
print("[INFO] loading EAST text detector...")
net = cv2.dnn.readNet(args["east"])

# if a video path was not supplied, grab the reference to the web cam
if not args.get("video", False):
    print('[INFO] starting video stream...')
    vs = VideoStream(src=0).start()
    time.sleep(1.0)

# otherwise grab a reference to the video file
else:
    cv2.VideoCapture(args["video"])

# start the FPS Counter
fps = FPS().start()

# loop over the Frames in the video stream
while True:
    # grab the current frame, then handle 
    frame = vs.read()
    frame = frame[1] if args.get("video", False) else frame

    # check to see if we reached end of stream
    if frame is None:
        break
    
    frame = imutils.resize(frame, width = 1000)
    orig = frame.copy()

    if W is None or H is None:
        (H, W) = frame.shape[:2]
        rW = W / float(newW)
        rH = H / float(newH)
    
    frame = cv2.resize(frame, (newW, newH))

    blob = cv2.dnn.blobFromImage(frame, 1.0, (newW, newH), (123.68, 116.78, 103.94), swapRB = True, crop = False)
    net.setInput(blob)
    (scores, geometry) = net.forward(layerNames)
    
    # decode predictions and apply NMS
    (rects, confidences) = decode_predictions(scores, geometry)
    boxes = non_max_suppression(np.array(rects), probs = confidences)

    # loop over the bounding boxes
    for (startX, startY, endX, endY) in boxes:
        # scale the bounding box coordinates based on respective ratios
        startX = int(startX * rW)
        startY = int(startY * rH)
        endX = int(endX * rW)
        endY = int(endY * rH)

        # draw the bounding box on the image
        cv2.rectangle(orig, (startX, startY), (endX, endY), (0, 255, 0), 2)

    # update the fps counter
    fps.update()

    # show the output frame
    cv2.imshow("text Detection", orig)
    key = cv2.waitKey(1) & 0xFF

    # if the 'q' key was pressed, break from the loop
    if key == ord('q'):
        break
    
# stop the timer
fps.stop()
print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx FPS: {:.2f}".format(fps.fps()))

# if using a webcam
if not args.get("video", False):
    vs.stop()
else:
    vs.release()

# close all windows
cv2.destroyAllWindows()
